"""Persistence pipeline — saves RawListings to the database.

Handles deduplication (by source + external_id), currency conversion,
and barrio matching via PostGIS point-in-polygon or name fuzzy match.
"""

from __future__ import annotations

import logging
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

    with Session(engine) as session:
        # Pre-load barrio name index for fast lookups
        barrios = {b.name.lower(): b.id for b in session.query(Barrio).all()}

        for raw in raw_listings:
            try:
                # Check if listing already exists
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
                    updated += 1
                else:
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
                        first_seen_at=now,
                        last_seen_at=now,
                        is_active=True,
                        days_on_market=0,
                    )
                    session.add(listing)
                    created += 1

            except Exception:
                logger.exception("Failed to save listing %s/%s", raw.source, raw.external_id)
                skipped += 1
                continue

        session.commit()

    engine.dispose()

    logger.info("Pipeline done: %d created, %d updated, %d skipped", created, updated, skipped)
    return {"created": created, "updated": updated, "skipped": skipped}
