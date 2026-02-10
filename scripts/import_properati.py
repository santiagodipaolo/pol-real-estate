#!/usr/bin/env python3
"""
Import script for Properati CSV data into the POL Real Estate database.

Reads a Properati CSV file, normalizes fields, geo-locates each listing to a
CABA barrio, and bulk-inserts records into the listings table.

Usage:
    python scripts/import_properati.py [--file PATH] [--ars-rate FLOAT] [--batch-size INT] [--dry-run]

Options:
    --file        Path to the Properati CSV file.
                  Default: data/raw/properati_caba.csv
    --ars-rate    ARS to USD conversion rate (blue rate).
                  If not supplied, the script will read the latest rate from the
                  currency_rates table or default to 1200.
    --batch-size  Number of records per INSERT batch. Default: 1000.
    --dry-run     Parse and validate but do not insert.
"""

import argparse
import csv
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup so we can import backend modules when running from project root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.barrio import Barrio
from app.models.listing import Listing
from app.models.currency_rate import CurrencyRate
from app.core.database import Base

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Bounding box for Ciudad Autonoma de Buenos Aires
CABA_LAT_MIN = -34.71
CABA_LAT_MAX = -34.52
CABA_LON_MIN = -58.53
CABA_LON_MAX = -58.33

OPERATION_MAP = {
    "venta": "sale",
    "sell": "sale",
    "sale": "sale",
    "alquiler": "rent",
    "rent": "rent",
    "alquiler temporario": "temporary_rent",
    "temporary_rent": "temporary_rent",
}

PROPERTY_TYPE_MAP = {
    "departamento": "apartment",
    "apartment": "apartment",
    "casa": "house",
    "house": "house",
    "ph": "ph",
    "terreno": "land",
    "land": "land",
    "lote": "land",
    "oficina": "office",
    "office": "office",
    "local": "commercial",
    "local comercial": "commercial",
    "cochera": "garage",
    "garage": "garage",
    "deposito": "warehouse",
    "bodega": "warehouse",
}

DEFAULT_ARS_RATE = 1200.0

# Expected CSV columns
EXPECTED_COLUMNS = {
    "id", "created_on", "operation", "property_type",
    "place_with_parent_names", "lat", "lon", "price", "currency",
    "surface_total", "surface_covered", "rooms",
}


@dataclass
class ImportStats:
    """Track import statistics."""
    total_rows: int = 0
    skipped_outside_caba: int = 0
    skipped_no_coords: int = 0
    skipped_no_price: int = 0
    skipped_unknown_operation: int = 0
    skipped_unknown_property_type: int = 0
    skipped_no_barrio: int = 0
    skipped_duplicate: int = 0
    converted_ars_to_usd: int = 0
    inserted: int = 0
    errors: int = 0
    batches: int = 0
    elapsed_seconds: float = 0.0

    def print_summary(self) -> None:
        logger.info("=" * 60)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info("Total rows processed:          %d", self.total_rows)
        logger.info("Inserted:                      %d", self.inserted)
        logger.info("Batches:                       %d", self.batches)
        logger.info("Skipped - outside CABA:        %d", self.skipped_outside_caba)
        logger.info("Skipped - no coordinates:      %d", self.skipped_no_coords)
        logger.info("Skipped - no price:            %d", self.skipped_no_price)
        logger.info("Skipped - unknown operation:   %d", self.skipped_unknown_operation)
        logger.info("Skipped - unknown prop. type:  %d", self.skipped_unknown_property_type)
        logger.info("Skipped - no barrio match:     %d", self.skipped_no_barrio)
        logger.info("Skipped - duplicate:           %d", self.skipped_duplicate)
        logger.info("ARS -> USD conversions:        %d", self.converted_ars_to_usd)
        logger.info("Errors:                        %d", self.errors)
        logger.info("Elapsed time:                  %.1f seconds", self.elapsed_seconds)
        if self.elapsed_seconds > 0 and self.inserted > 0:
            logger.info(
                "Throughput:                    %.0f rows/sec",
                self.inserted / self.elapsed_seconds,
            )
        logger.info("=" * 60)


def _safe_decimal(value: str) -> Optional[Decimal]:
    """Parse a string into a Decimal, returning None for empty or invalid values."""
    if not value or value.strip() == "":
        return None
    try:
        d = Decimal(value.strip())
        if d.is_nan() or d.is_infinite():
            return None
        return d
    except (InvalidOperation, ValueError):
        return None


def _safe_int(value: str) -> Optional[int]:
    """Parse a string into an int, returning None for empty or invalid values."""
    if not value or value.strip() == "":
        return None
    try:
        f = float(value.strip())
        return int(f)
    except (ValueError, TypeError):
        return None


def _safe_float(value: str) -> Optional[float]:
    """Parse a string into a float, returning None for empty or invalid values."""
    if not value or value.strip() == "":
        return None
    try:
        f = float(value.strip())
        if f != f:  # NaN check
            return None
        return f
    except (ValueError, TypeError):
        return None


def get_latest_ars_rate(session) -> Optional[float]:
    """Fetch the latest ARS/USD blue rate from the currency_rates table."""
    try:
        rate = (
            session.query(CurrencyRate)
            .filter(CurrencyRate.rate_type == "blue")
            .order_by(CurrencyRate.recorded_at.desc())
            .first()
        )
        if rate and rate.sell:
            return float(rate.sell)
    except Exception as exc:
        logger.warning("Could not fetch ARS rate from DB: %s", exc)
    return None


def build_barrio_lookup(session) -> dict:
    """
    Build a lookup of barrio_id by querying PostGIS ST_Contains.

    Returns a callable that maps (lat, lon) -> barrio_id or None.
    The function caches results per-point.
    """
    barrios = session.query(
        Barrio.id, Barrio.name, Barrio.geometry
    ).filter(Barrio.geometry.isnot(None)).all()

    if not barrios:
        logger.warning(
            "No barrios with geometry found. Run seed_barrios.py first. "
            "Will attempt ST_Contains query per-point instead."
        )
        return None

    logger.info("Loaded %d barrios with geometry for spatial lookup.", len(barrios))
    return barrios


def find_barrio_id_postgis(session, lat: float, lon: float) -> Optional[int]:
    """Use PostGIS ST_Contains to find which barrio contains the given point."""
    result = session.execute(
        text(
            "SELECT id FROM barrios "
            "WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) "
            "LIMIT 1"
        ),
        {"lat": lat, "lon": lon},
    ).fetchone()
    if result:
        return result[0]
    return None


def import_properati(
    file_path: str,
    ars_rate: float,
    batch_size: int = 1000,
    dry_run: bool = False,
) -> ImportStats:
    """
    Main import function.

    Reads the CSV, normalizes data, resolves barrios, and bulk-inserts
    Listing records.
    """
    stats = ImportStats()
    start_time = time.time()

    db_url = settings.sync_database_url
    logger.info("Connecting to database: %s", db_url.split("@")[-1])

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    if not os.path.isfile(file_path):
        logger.error("CSV file not found: %s", file_path)
        stats.errors = 1
        return stats

    try:
        # Pre-load existing external IDs to skip duplicates
        logger.info("Loading existing external IDs for deduplication...")
        existing_ids = set()
        for row in session.execute(
            text("SELECT external_id FROM listings WHERE source = 'properati'")
        ):
            existing_ids.add(row[0])
        logger.info("Found %d existing Properati listings.", len(existing_ids))

        # ARS rate
        if ars_rate is None:
            ars_rate = get_latest_ars_rate(session)
            if ars_rate:
                logger.info("Using latest ARS/USD rate from DB: %.2f", ars_rate)
            else:
                ars_rate = DEFAULT_ARS_RATE
                logger.info("Using default ARS/USD rate: %.2f", ars_rate)
        else:
            logger.info("Using provided ARS/USD rate: %.2f", ars_rate)

        # Open CSV
        logger.info("Reading CSV: %s", file_path)
        batch: list[Listing] = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Validate columns
            if reader.fieldnames:
                available = set(reader.fieldnames)
                missing = EXPECTED_COLUMNS - available
                if missing:
                    logger.warning(
                        "CSV is missing expected columns: %s. "
                        "Will proceed but some fields may be None.",
                        missing,
                    )

            for row in reader:
                stats.total_rows += 1

                try:
                    external_id = (row.get("id") or "").strip()
                    if not external_id:
                        stats.errors += 1
                        continue

                    # Duplicate check
                    if external_id in existing_ids:
                        stats.skipped_duplicate += 1
                        continue

                    # --- Coordinates ---
                    lat = _safe_float(row.get("lat", ""))
                    lon = _safe_float(row.get("lon", ""))

                    if lat is None or lon is None:
                        stats.skipped_no_coords += 1
                        continue

                    # --- CABA bounding box filter ---
                    if not (CABA_LAT_MIN <= lat <= CABA_LAT_MAX and CABA_LON_MIN <= lon <= CABA_LON_MAX):
                        stats.skipped_outside_caba += 1
                        continue

                    # --- Operation type ---
                    raw_operation = (row.get("operation") or "").strip().lower()
                    operation_type = OPERATION_MAP.get(raw_operation)
                    if not operation_type:
                        stats.skipped_unknown_operation += 1
                        continue

                    # --- Property type ---
                    raw_property_type = (row.get("property_type") or "").strip().lower()
                    property_type = PROPERTY_TYPE_MAP.get(raw_property_type, raw_property_type)
                    if not property_type:
                        stats.skipped_unknown_property_type += 1
                        continue

                    # --- Price ---
                    price = _safe_decimal(row.get("price", ""))
                    currency = (row.get("currency") or "").strip().upper()

                    if price is None or price <= 0:
                        stats.skipped_no_price += 1
                        continue

                    # Compute USD and ARS prices
                    price_usd_blue = None
                    price_ars = None
                    currency_original = currency if currency else None

                    if currency == "USD":
                        price_usd_blue = price
                        price_ars = price * Decimal(str(ars_rate))
                    elif currency in ("ARS", "ARS$", "$"):
                        currency_original = "ARS"
                        price_ars = price
                        price_usd_blue = price / Decimal(str(ars_rate))
                        stats.converted_ars_to_usd += 1
                    else:
                        # Unknown currency -- store as-is
                        price_usd_blue = price
                        price_ars = price * Decimal(str(ars_rate))

                    # --- Barrio assignment via PostGIS ---
                    barrio_id = find_barrio_id_postgis(session, lat, lon)
                    if barrio_id is None:
                        stats.skipped_no_barrio += 1
                        continue

                    # --- Surfaces ---
                    surface_total = _safe_decimal(row.get("surface_total", ""))
                    surface_covered = _safe_decimal(row.get("surface_covered", ""))
                    rooms = _safe_int(row.get("rooms", ""))

                    # --- Geometry ---
                    point = Point(lon, lat)
                    location = from_shape(point, srid=4326)

                    # --- Build Listing ---
                    listing = Listing(
                        id=uuid.uuid4(),
                        external_id=external_id,
                        source="properati",
                        url=(row.get("url") or "").strip() or None,
                        title=(row.get("title") or "").strip() or None,
                        operation_type=operation_type,
                        property_type=property_type,
                        price_original=price,
                        currency_original=currency_original,
                        price_usd_blue=price_usd_blue,
                        price_ars=price_ars,
                        surface_total_m2=surface_total,
                        surface_covered_m2=surface_covered,
                        rooms=rooms,
                        latitude=Decimal(str(round(lat, 7))),
                        longitude=Decimal(str(round(lon, 7))),
                        location=location,
                        barrio_id=barrio_id,
                        is_active=True,
                    )

                    batch.append(listing)
                    existing_ids.add(external_id)  # prevent intra-file duplicates

                    # Flush batch
                    if len(batch) >= batch_size:
                        if not dry_run:
                            session.bulk_save_objects(batch)
                            session.commit()
                        stats.inserted += len(batch)
                        stats.batches += 1
                        logger.info(
                            "Batch %d committed (%d records). Total inserted: %d / %d processed.",
                            stats.batches,
                            len(batch),
                            stats.inserted,
                            stats.total_rows,
                        )
                        batch = []

                except Exception as exc:
                    stats.errors += 1
                    if stats.errors <= 10:
                        logger.warning(
                            "Error processing row %d: %s", stats.total_rows, exc
                        )
                    elif stats.errors == 11:
                        logger.warning("Suppressing further row-level error messages.")
                    continue

        # Final batch
        if batch:
            if not dry_run:
                session.bulk_save_objects(batch)
                session.commit()
            stats.inserted += len(batch)
            stats.batches += 1
            logger.info(
                "Final batch committed (%d records). Total inserted: %d.",
                len(batch),
                stats.inserted,
            )

    except Exception:
        session.rollback()
        logger.exception("Fatal error during import.")
        raise
    finally:
        session.close()
        engine.dispose()

    stats.elapsed_seconds = time.time() - start_time
    return stats


def main() -> None:
    default_csv = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "raw", "properati_caba.csv")
    )

    parser = argparse.ArgumentParser(
        description="Import Properati CSV data into POL Real Estate database."
    )
    parser.add_argument(
        "--file",
        type=str,
        default=default_csv,
        help=f"Path to the Properati CSV file. Default: {default_csv}",
    )
    parser.add_argument(
        "--ars-rate",
        type=float,
        default=None,
        help="ARS to USD conversion rate (blue). Auto-detected from DB if omitted.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of records per INSERT batch. Default: 1000.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate data without inserting into the database.",
    )
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN mode -- no data will be inserted.")

    stats = import_properati(
        file_path=args.file,
        ars_rate=args.ars_rate,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    stats.print_summary()


if __name__ == "__main__":
    main()
