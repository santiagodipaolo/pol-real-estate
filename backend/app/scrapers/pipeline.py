"""Persistence pipeline — saves RawListings to the database.

Handles deduplication (by source + external_id), currency conversion,
barrio matching via PostGIS point-in-polygon or name fuzzy match,
and cross-source dedup via fingerprinting.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.barrio import Barrio
from app.models.listing import Listing
from app.scrapers.base import RawListing

logger = logging.getLogger(__name__)


def _normalize_address(address: str | None) -> str:
    """Normalize an address for fingerprinting.

    Strips accents, lowercases, removes common abbreviations and noise.
    'Av. Santa Fe 1234 3°B' -> 'santa fe 1234'
    """
    if not address:
        return ""
    # Remove accents
    s = unicodedata.normalize("NFD", address)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().strip()
    # Remove floor/unit info (3°B, piso 5, dto A, etc.)
    s = re.sub(r"\b(piso|dto|depto|departamento|unidad|uf|pb|ep)\b.*", "", s)
    s = re.sub(r"\d+[°ºª]\s*[a-z]?\b", "", s)
    # Normalize common abbreviations (longer words first to avoid partial matches)
    s = re.sub(r"\bavenida\s+", "", s)
    s = re.sub(r"\bboulevard\s+", "", s)
    s = re.sub(r"\bpasaje\s+", "", s)
    s = re.sub(r"\bcalle\s+", "", s)
    s = re.sub(r"\bav\.?\s*", "", s)
    s = re.sub(r"\bblvd\.?\s*", "", s)
    s = re.sub(r"\bpje\.?\s*", "", s)
    # Remove extra whitespace and punctuation leftovers
    s = re.sub(r"[.,;]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _round_surface(surface: float | None) -> int:
    """Round surface to nearest 5m² for fuzzy matching."""
    if not surface or surface <= 0:
        return 0
    return round(surface / 5) * 5


def compute_fingerprint(raw: RawListing) -> str | None:
    """Compute a fingerprint for cross-source deduplication.

    fingerprint = sha256(normalized_address | surface_5m² | rooms | operation)
    Returns None if not enough data to fingerprint (no address or surface).
    """
    addr = _normalize_address(raw.address)
    surface = _round_surface(raw.surface_total_m2)

    if not addr or not surface:
        return None

    rooms = raw.rooms or 0
    key = f"{addr}|{surface}|{rooms}|{raw.operation_type}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _get_blue_rate() -> float | None:
    """Fetch current blue dollar rate from DolarAPI."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{settings.DOLAR_API_BASE_URL}/dolares/blue")
            resp.raise_for_status()
            data = resp.json()
            return float(data.get("venta", 0)) or None
    except Exception:
        logger.warning("Could not fetch blue dollar rate")
        return None


def _match_barrio_by_name(session: Session, name: str | None) -> int | None:
    """Try to find a barrio by name (case-insensitive, partial match)."""
    if not name:
        return None
    name_clean = name.strip().lower()
    result = session.execute(
        select(Barrio.id).where(Barrio.name.ilike(f"%{name_clean}%"))
    ).scalar_one_or_none()
    return result


def _match_barrio_by_point(session: Session, lat: float, lon: float) -> int | None:
    """Try to find a barrio containing the given lat/lng using GeoJSON geometry."""
    if not lat or not lon:
        return None
    # Since geometry is stored as JSONB (GeoJSON), we use a raw SQL approach
    # with ST_Contains on the JSONB geometry cast to geometry type
    try:
        result = session.execute(
            text("""
                SELECT id FROM barrios
                WHERE ST_Contains(
                    ST_SetSRID(ST_GeomFromGeoJSON(geometry::text), 4326),
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                )
                LIMIT 1
            """),
            {"lat": lat, "lon": lon},
        ).scalar_one_or_none()
        return result
    except Exception:
        logger.debug("PostGIS point-in-polygon failed, falling back to name match")
        return None


def save_listings(raw_listings: list[RawListing]) -> dict:
    """Save a batch of RawListings to the database.

    Returns a summary dict with counts of created/updated/skipped listings.
    """
    if not raw_listings:
        return {"created": 0, "updated": 0, "skipped": 0}

    engine = create_engine(settings.sync_database_url)
    blue_rate = _get_blue_rate()

    created = 0
    updated = 0
    skipped = 0
    deduped = 0

    with Session(engine) as session:
        # Pre-load barrio name index for fast lookups
        barrios = {b.name.lower(): b.id for b in session.query(Barrio).all()}

        # Pre-load existing fingerprints for cross-source dedup
        fp_index: dict[str, uuid.UUID] = {}
        fp_rows = session.execute(
            select(Listing.fingerprint, Listing.id).where(
                Listing.fingerprint.isnot(None),
                Listing.canonical_id.is_(None),
            )
        ).all()
        for fp, lid in fp_rows:
            fp_index[fp] = lid

        for raw in raw_listings:
            try:
                # Check if listing already exists (same source)
                existing = session.execute(
                    select(Listing).where(
                        Listing.source == raw.source,
                        Listing.external_id == raw.external_id,
                    )
                ).scalar_one_or_none()

                # Match barrio
                barrio_id = None
                if raw.latitude and raw.longitude:
                    barrio_id = _match_barrio_by_point(session, raw.latitude, raw.longitude)
                if not barrio_id and raw.barrio_name:
                    name_lower = raw.barrio_name.strip().lower()
                    barrio_id = barrios.get(name_lower)
                    if not barrio_id:
                        # Fuzzy: check if barrio_name is contained in any barrio name
                        for bname, bid in barrios.items():
                            if name_lower in bname or bname in name_lower:
                                barrio_id = bid
                                break

                # Convert prices
                price_usd_blue = None
                price_ars = None
                if raw.price and raw.currency == "USD":
                    price_usd_blue = Decimal(str(raw.price))
                    if blue_rate:
                        price_ars = Decimal(str(raw.price * blue_rate))
                elif raw.price and raw.currency == "ARS":
                    price_ars = Decimal(str(raw.price))
                    if blue_rate:
                        price_usd_blue = Decimal(str(raw.price / blue_rate))

                now = datetime.now(timezone.utc)

                # Compute fingerprint for cross-source dedup
                fp = compute_fingerprint(raw)

                if existing:
                    # Update: refresh price, last_seen, active status
                    existing.price_original = Decimal(str(raw.price)) if raw.price else existing.price_original
                    existing.currency_original = raw.currency
                    existing.price_usd_blue = price_usd_blue or existing.price_usd_blue
                    existing.price_ars = price_ars or existing.price_ars
                    existing.last_seen_at = now
                    existing.is_active = True
                    existing.days_on_market = (now - existing.first_seen_at).days
                    if raw.surface_total_m2 and not existing.surface_total_m2:
                        existing.surface_total_m2 = Decimal(str(raw.surface_total_m2))
                    if raw.surface_covered_m2 and not existing.surface_covered_m2:
                        existing.surface_covered_m2 = Decimal(str(raw.surface_covered_m2))
                    if raw.latitude and not existing.latitude:
                        existing.latitude = Decimal(str(raw.latitude))
                        existing.longitude = Decimal(str(raw.longitude))
                    if barrio_id and not existing.barrio_id:
                        existing.barrio_id = barrio_id
                    if fp and not existing.fingerprint:
                        existing.fingerprint = fp
                    updated += 1
                else:
                    # Check cross-source duplicate via fingerprint
                    canonical_id = None
                    if fp and fp in fp_index:
                        canonical_id = fp_index[fp]
                        deduped += 1
                        logger.debug(
                            "Cross-source dup: %s/%s -> canonical %s (fp=%s)",
                            raw.source, raw.external_id, canonical_id, fp,
                        )

                    # Create new listing
                    listing = Listing(
                        external_id=raw.external_id,
                        source=raw.source,
                        url=raw.url,
                        title=raw.title,
                        operation_type=raw.operation_type,
                        property_type=raw.property_type,
                        price_original=Decimal(str(raw.price)) if raw.price else None,
                        currency_original=raw.currency,
                        price_usd_blue=price_usd_blue,
                        price_ars=price_ars,
                        expenses_ars=Decimal(str(raw.expenses_ars)) if raw.expenses_ars else None,
                        surface_total_m2=Decimal(str(raw.surface_total_m2)) if raw.surface_total_m2 else None,
                        surface_covered_m2=Decimal(str(raw.surface_covered_m2)) if raw.surface_covered_m2 else None,
                        rooms=raw.rooms,
                        bedrooms=raw.bedrooms,
                        bathrooms=raw.bathrooms,
                        garages=raw.garages,
                        age_years=raw.age_years,
                        amenities=raw.amenities or None,
                        latitude=Decimal(str(raw.latitude)) if raw.latitude else None,
                        longitude=Decimal(str(raw.longitude)) if raw.longitude else None,
                        barrio_id=barrio_id,
                        fingerprint=fp,
                        canonical_id=canonical_id,
                        first_seen_at=now,
                        last_seen_at=now,
                        is_active=True,
                        days_on_market=0,
                    )
                    session.add(listing)
                    created += 1

                    # Register fingerprint for this batch
                    if fp and not canonical_id:
                        fp_index[fp] = listing.id

            except Exception:
                logger.exception("Failed to save listing %s/%s", raw.source, raw.external_id)
                skipped += 1
                continue

        session.commit()

    engine.dispose()

    logger.info(
        "Pipeline done: %d created, %d updated, %d skipped, %d cross-source dups",
        created, updated, skipped, deduped,
    )
    return {"created": created, "updated": updated, "skipped": skipped, "deduped": deduped}
