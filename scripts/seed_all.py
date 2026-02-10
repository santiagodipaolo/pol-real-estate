#!/usr/bin/env python3
"""
Seed script for POL Real Estate.

Seeds barrios from Buenos Aires Open Data, fetches current currency rates,
and creates sample barrio_snapshots with realistic data.

Usage:
    python scripts/seed_all.py
"""

import json
import logging
import os
import sys
import random
from datetime import date, timedelta, datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models.barrio import Barrio
from app.models.barrio_snapshot import BarrioSnapshot
from app.models.currency_rate import CurrencyRate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Barrio data: name -> (comuna_id, comuna_name)
# ---------------------------------------------------------------------------
BARRIO_COMUNAS = {
    "Agronomía": (15, "Comuna 15"), "Almagro": (5, "Comuna 5"),
    "Balvanera": (3, "Comuna 3"), "Barracas": (4, "Comuna 4"),
    "Belgrano": (13, "Comuna 13"), "Boca": (4, "Comuna 4"),
    "Boedo": (5, "Comuna 5"), "Caballito": (6, "Comuna 6"),
    "Chacarita": (15, "Comuna 15"), "Coghlan": (12, "Comuna 12"),
    "Colegiales": (13, "Comuna 13"), "Constitución": (1, "Comuna 1"),
    "Flores": (7, "Comuna 7"), "Floresta": (10, "Comuna 10"),
    "La Boca": (4, "Comuna 4"), "La Paternal": (15, "Comuna 15"),
    "Liniers": (9, "Comuna 9"), "Mataderos": (9, "Comuna 9"),
    "Monte Castro": (10, "Comuna 10"), "Montserrat": (1, "Comuna 1"),
    "Nueva Pompeya": (4, "Comuna 4"), "Núñez": (13, "Comuna 13"),
    "Palermo": (14, "Comuna 14"), "Parque Avellaneda": (9, "Comuna 9"),
    "Parque Chacabuco": (7, "Comuna 7"), "Parque Chas": (15, "Comuna 15"),
    "Parque Patricios": (4, "Comuna 4"), "Puerto Madero": (1, "Comuna 1"),
    "Recoleta": (2, "Comuna 2"), "Retiro": (1, "Comuna 1"),
    "Saavedra": (12, "Comuna 12"), "San Cristóbal": (3, "Comuna 3"),
    "San Nicolás": (1, "Comuna 1"), "San Telmo": (1, "Comuna 1"),
    "Vélez Sársfield": (10, "Comuna 10"), "Versalles": (10, "Comuna 10"),
    "Villa Crespo": (15, "Comuna 15"), "Villa del Parque": (11, "Comuna 11"),
    "Villa Devoto": (11, "Comuna 11"), "Villa General Mitre": (11, "Comuna 11"),
    "Villa Lugano": (8, "Comuna 8"), "Villa Luro": (10, "Comuna 10"),
    "Villa Ortúzar": (15, "Comuna 15"), "Villa Pueyrredón": (12, "Comuna 12"),
    "Villa Real": (10, "Comuna 10"), "Villa Riachuelo": (8, "Comuna 8"),
    "Villa Santa Rita": (11, "Comuna 11"), "Villa Soldati": (8, "Comuna 8"),
    "Villa Urquiza": (12, "Comuna 12"),
}


def slugify(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace(" ", "-")
    for ch in "'.()":
        s = s.replace(ch, "")
    return s


# ---------------------------------------------------------------------------
# Realistic price data by barrio (approximate USD/m2 ranges for sale)
# ---------------------------------------------------------------------------
BARRIO_PRICE_RANGES = {
    "Puerto Madero": (4500, 6500), "Palermo": (2800, 3800),
    "Belgrano": (2600, 3400), "Recoleta": (2500, 3500),
    "Núñez": (2400, 3100), "Colegiales": (2300, 3000),
    "Caballito": (2000, 2700), "Villa Crespo": (2100, 2800),
    "Villa Urquiza": (2000, 2600), "Coghlan": (2000, 2500),
    "Saavedra": (1900, 2500), "Almagro": (1800, 2400),
    "Villa Devoto": (1800, 2300), "Chacarita": (1900, 2500),
    "Villa del Parque": (1700, 2200), "Boedo": (1700, 2300),
    "Parque Chacabuco": (1600, 2100), "San Telmo": (1800, 2500),
    "Montserrat": (1500, 2100), "Retiro": (2000, 3000),
    "Constitución": (1200, 1800), "San Nicolás": (1500, 2200),
    "Flores": (1500, 2000), "Barracas": (1500, 2100),
    "Villa Pueyrredón": (1600, 2100), "Villa Ortúzar": (1900, 2500),
    "Parque Chas": (1800, 2300), "La Paternal": (1600, 2100),
    "Villa General Mitre": (1600, 2100), "Agronomía": (1700, 2200),
    "Monte Castro": (1500, 2000), "Floresta": (1400, 1900),
    "Vélez Sársfield": (1400, 1800), "Villa Real": (1300, 1700),
    "Villa Luro": (1400, 1800), "Villa Santa Rita": (1500, 2000),
    "Versalles": (1300, 1700), "Liniers": (1200, 1700),
    "Mataderos": (1100, 1600), "Parque Avellaneda": (1100, 1500),
    "Parque Patricios": (1500, 2200), "Nueva Pompeya": (1000, 1500),
    "La Boca": (1100, 1700), "Boca": (1100, 1700),
    "San Cristóbal": (1400, 1900), "Balvanera": (1400, 2000),
    "Villa Lugano": (800, 1200), "Villa Soldati": (800, 1200),
    "Villa Riachuelo": (700, 1100),
}


def seed_barrios(session):
    """Seed barrios from BA Open Data GeoJSON."""
    existing = session.query(Barrio).count()
    if existing > 0:
        logger.info(f"Barrios already seeded ({existing} records). Skipping.")
        return

    # Try to fetch GeoJSON from BA Open Data
    geojson_data = None
    try:
        url = "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-educacion/barrios/barrios.geojson"
        logger.info(f"Fetching barrios GeoJSON from {url}")
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        geojson_data = resp.json()
        logger.info(f"Downloaded {len(geojson_data.get('features', []))} features")
    except Exception as e:
        logger.warning(f"Could not fetch GeoJSON: {e}. Will seed without geometry.")

    # Build lookup without accents for matching
    import unicodedata as _ud
    def _strip_accents(s):
        return "".join(c for c in _ud.normalize("NFKD", s) if not _ud.combining(c))

    barrio_lookup = {}
    for k, v in BARRIO_COMUNAS.items():
        barrio_lookup[_strip_accents(k).lower()] = (k, v[0], v[1])

    if geojson_data and "features" in geojson_data:
        for feat in geojson_data["features"]:
            props = feat.get("properties", {})
            # Try multiple property names
            name = (props.get("nombre") or props.get("BARRIO")
                    or props.get("barrio") or props.get("name") or "").strip()
            if not name:
                continue

            # Lookup comuna using accent-stripped comparison
            name_key = _strip_accents(name).lower()
            if name_key in barrio_lookup:
                canonical_name, comuna_id, comuna_name = barrio_lookup[name_key]
                name = canonical_name  # Use our accented version
            else:
                # Direct match
                comuna_id, comuna_name = BARRIO_COMUNAS.get(name, (0, "Desconocida"))
                if comuna_id == 0:
                    # Use data from GeoJSON itself
                    comuna_id = props.get("comuna", 0)
                    comuna_name = f"Comuna {comuna_id}" if comuna_id else "Desconocida"

            geometry = feat.get("geometry")

            # Compute centroid from geometry coordinates
            centroid_lat, centroid_lon = None, None
            if geometry and geometry.get("coordinates"):
                coords = geometry["coordinates"]
                try:
                    # Flatten all coordinate pairs
                    all_coords = []
                    def flatten(c):
                        if isinstance(c[0], (int, float)):
                            all_coords.append(c)
                        else:
                            for sub in c:
                                flatten(sub)
                    flatten(coords)
                    if all_coords:
                        centroid_lon = sum(c[0] for c in all_coords) / len(all_coords)
                        centroid_lat = sum(c[1] for c in all_coords) / len(all_coords)
                except Exception:
                    pass

            barrio = Barrio(
                name=name,
                slug=slugify(name),
                comuna_id=comuna_id,
                comuna_name=comuna_name,
                geometry=geometry,
                centroid_lat=centroid_lat,
                centroid_lon=centroid_lon,
            )
            session.add(barrio)
            logger.info(f"  Added barrio: {name} (Comuna {comuna_id})")
    else:
        # Fallback: seed without geometry
        for name, (comuna_id, comuna_name) in BARRIO_COMUNAS.items():
            barrio = Barrio(
                name=name,
                slug=slugify(name),
                comuna_id=comuna_id,
                comuna_name=comuna_name,
            )
            session.add(barrio)
            logger.info(f"  Added barrio (no geometry): {name}")

    session.commit()
    count = session.query(Barrio).count()
    logger.info(f"Seeded {count} barrios successfully.")


def seed_currency_rates(session):
    """Fetch current currency rates from DolarAPI."""
    existing = session.query(CurrencyRate).count()
    if existing > 0:
        logger.info(f"Currency rates already exist ({existing} records). Skipping.")
        return

    rate_types = {
        "blue": "https://dolarapi.com/v1/dolares/blue",
        "official": "https://dolarapi.com/v1/dolares/oficial",
        "mep": "https://dolarapi.com/v1/dolares/bolsa",
        "ccl": "https://dolarapi.com/v1/dolares/contadoconliqui",
    }

    for rate_type, url in rate_types.items():
        try:
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            rate = CurrencyRate(
                rate_type=rate_type,
                buy=data.get("compra"),
                sell=data.get("venta"),
                source="dolarapi",
                recorded_at=datetime.now(timezone.utc),
            )
            session.add(rate)
            logger.info(f"  Fetched {rate_type}: buy={data.get('compra')}, sell={data.get('venta')}")
        except Exception as e:
            logger.warning(f"  Failed to fetch {rate_type}: {e}")

    session.commit()
    logger.info("Currency rates seeded.")


def seed_barrio_snapshots(session):
    """Create realistic barrio_snapshots data for the dashboard to display."""
    existing = session.query(BarrioSnapshot).count()
    if existing > 0:
        logger.info(f"Snapshots already exist ({existing} records). Skipping.")
        return

    barrios = session.query(Barrio).all()
    if not barrios:
        logger.warning("No barrios found. Run seed_barrios first.")
        return

    today = date.today()
    # Create snapshots for the last 30 days
    dates = [today - timedelta(days=i) for i in range(30)]

    for barrio in barrios:
        price_range = BARRIO_PRICE_RANGES.get(barrio.name, (1500, 2500))
        base_price = random.uniform(price_range[0], price_range[1])
        listing_count = random.randint(20, 300)

        for snap_date in dates:
            # Add some daily variation
            daily_var = random.uniform(-0.02, 0.02)
            median_price = round(base_price * (1 + daily_var), 2)
            avg_price = round(median_price * random.uniform(0.95, 1.05), 2)
            p25 = round(median_price * random.uniform(0.75, 0.85), 2)
            p75 = round(median_price * random.uniform(1.15, 1.30), 2)

            # Sale snapshot
            snapshot = BarrioSnapshot(
                barrio_id=barrio.id,
                snapshot_date=snap_date,
                operation_type="sale",
                listing_count=listing_count + random.randint(-10, 10),
                median_price_usd_m2=median_price,
                avg_price_usd_m2=avg_price,
                p25_price_usd_m2=p25,
                p75_price_usd_m2=p75,
                avg_days_on_market=round(random.uniform(30, 180), 1),
                new_listings_7d=random.randint(2, 30),
                removed_listings_7d=random.randint(1, 15),
                rental_yield_estimate=round(random.uniform(0.03, 0.08), 4),
                usd_blue_rate=1200.0,
            )
            session.add(snapshot)

            # Rent snapshot (monthly rent per m2, roughly 0.3-0.5% of sale price)
            rent_price = round(base_price * random.uniform(0.003, 0.005), 2)
            rent_snapshot = BarrioSnapshot(
                barrio_id=barrio.id,
                snapshot_date=snap_date,
                operation_type="rent",
                listing_count=random.randint(10, 150),
                median_price_usd_m2=rent_price,
                avg_price_usd_m2=round(rent_price * random.uniform(0.95, 1.05), 2),
                avg_days_on_market=round(random.uniform(15, 60), 1),
                new_listings_7d=random.randint(1, 20),
                removed_listings_7d=random.randint(1, 10),
            )
            session.add(rent_snapshot)

    session.commit()
    count = session.query(BarrioSnapshot).count()
    logger.info(f"Seeded {count} barrio snapshots.")


def main():
    engine = create_engine(settings.sync_database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        logger.info("=" * 60)
        logger.info("POL Real Estate - Data Seeder")
        logger.info("=" * 60)

        logger.info("\n--- Seeding Barrios ---")
        seed_barrios(session)

        logger.info("\n--- Fetching Currency Rates ---")
        seed_currency_rates(session)

        logger.info("\n--- Generating Barrio Snapshots ---")
        seed_barrio_snapshots(session)

        logger.info("\n" + "=" * 60)
        logger.info("Seeding complete!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Seeding failed: {e}", exc_info=True)
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
