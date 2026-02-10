#!/usr/bin/env python3
"""
Seed script for Buenos Aires (CABA) barrios.

Downloads the GeoJSON of the 48 CABA barrios from Buenos Aires Open Data API,
or falls back to an embedded constant mapping, and inserts Barrio records
into the database.

Usage:
    python scripts/seed_barrios.py [--force]

Options:
    --force   Drop and recreate all barrio records even if they already exist.
"""

import argparse
import json
import logging
import os
import sys
import unicodedata
import re

# ---------------------------------------------------------------------------
# Path setup so we can import backend modules when running from project root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import httpx
from shapely.geometry import shape, MultiPolygon
from shapely.ops import transform
from geoalchemy2.shape import from_shape
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.barrio import Barrio
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
BA_GEOJSON_URL = (
    "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
    "ministerio-de-educacion/barrios/barrios.geojson"
)

# Fallback: the 48 CABA barrios grouped by comuna.
BARRIOS_POR_COMUNA: dict[int, list[str]] = {
    1: ["Retiro", "San Nicolás", "Puerto Madero", "San Telmo", "Montserrat", "Constitución"],
    2: ["Recoleta"],
    3: ["Balvanera", "San Cristóbal"],
    4: ["La Boca", "Barracas", "Parque Patricios", "Nueva Pompeya"],
    5: ["Almagro", "Boedo"],
    6: ["Caballito"],
    7: ["Flores", "Parque Chacabuco"],
    8: ["Villa Soldati", "Villa Riachuelo", "Villa Lugano"],
    9: ["Liniers", "Mataderos", "Parque Avellaneda"],
    10: ["Villa Real", "Monte Castro", "Versalles", "Floresta", "Vélez Sarsfield", "Villa Luro"],
    11: ["Villa General Mitre", "Villa Devoto", "Villa del Parque", "Villa Santa Rita"],
    12: ["Coghlan", "Saavedra", "Villa Urquiza", "Villa Pueyrredón"],
    13: ["Núñez", "Belgrano", "Colegiales"],
    14: ["Palermo"],
    15: ["Chacarita", "Villa Crespo", "La Paternal", "Villa Ortúzar", "Agronomía", "Parque Chas"],
}

# Build a fast lookup: barrio_name -> comuna_id
_BARRIO_TO_COMUNA: dict[str, int] = {}
for _comuna, _names in BARRIOS_POR_COMUNA.items():
    for _name in _names:
        _BARRIO_TO_COMUNA[_name] = _comuna


def slugify(value: str) -> str:
    """Convert a string to a URL-friendly slug."""
    # Normalize unicode and strip accents
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value


def _normalize_barrio_name(raw_name: str) -> str:
    """Normalize a barrio name coming from GeoJSON to match our canonical list."""
    # The GeoJSON may use ALL-CAPS or slight variations
    name = raw_name.strip().title()
    # Common corrections
    corrections = {
        "San Nicolas": "San Nicolás",
        "San Cristobal": "San Cristóbal",
        "Nuñez": "Núñez",
        "Nunez": "Núñez",
        "Velez Sarsfield": "Vélez Sarsfield",
        "Velez Sársfield": "Vélez Sarsfield",
        "Villa Pueyrredon": "Villa Pueyrredón",
        "Constitucion": "Constitución",
        "Villa Ortuzar": "Villa Ortúzar",
        "Agronomia": "Agronomía",
        "Parque Chas": "Parque Chas",
        "Parque Curi": "Parque Chas",  # possible alternate name
    }
    return corrections.get(name, name)


def _compute_area_km2(geom: MultiPolygon) -> float:
    """
    Approximate area in km2 for a geometry in EPSG:4326.

    Uses a simple cosine-of-latitude scaling. For Buenos Aires this is
    accurate enough for display purposes.
    """
    import math

    centroid = geom.centroid
    lat_rad = math.radians(centroid.y)
    # Degrees to metres at this latitude
    m_per_deg_lat = 111_132.0
    m_per_deg_lon = 111_132.0 * math.cos(lat_rad)

    def project(lon, lat):
        return (lon * m_per_deg_lon, lat * m_per_deg_lat)

    projected = transform(project, geom)
    return projected.area / 1_000_000  # m2 -> km2


def fetch_geojson() -> dict | None:
    """Try to download the GeoJSON from Buenos Aires Open Data."""
    logger.info("Attempting to download barrios GeoJSON from %s ...", BA_GEOJSON_URL)
    try:
        resp = httpx.get(BA_GEOJSON_URL, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        if data.get("type") == "FeatureCollection" and data.get("features"):
            logger.info(
                "Downloaded GeoJSON with %d features.", len(data["features"])
            )
            return data
        logger.warning("GeoJSON response did not contain features.")
        return None
    except Exception as exc:
        logger.warning("Failed to download GeoJSON: %s", exc)
        return None


def load_local_geojson() -> dict | None:
    """Try to load a locally cached GeoJSON from data/seeds/."""
    local_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "seeds", "barrios.geojson"
    )
    local_path = os.path.abspath(local_path)
    if os.path.isfile(local_path):
        logger.info("Loading local GeoJSON from %s", local_path)
        with open(local_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("type") == "FeatureCollection" and data.get("features"):
            return data
    return None


def build_barrio_records_from_geojson(geojson: dict) -> list[dict]:
    """Parse GeoJSON features into a list of dicts ready for insertion."""
    records = []
    for feature in geojson["features"]:
        props = feature.get("properties", {})
        geom_json = feature.get("geometry")
        if not geom_json:
            continue

        # Try different property key names used by BA Open Data
        raw_name = (
            props.get("BARRIO")
            or props.get("barrio")
            or props.get("nombre")
            or props.get("NOMBRE")
            or ""
        )
        if not raw_name:
            logger.warning("Feature with no barrio name, skipping: %s", props)
            continue

        name = _normalize_barrio_name(raw_name)
        comuna_id = _BARRIO_TO_COMUNA.get(name)

        # Try to get comuna from properties if our lookup fails
        if comuna_id is None:
            raw_comuna = props.get("COMUNA") or props.get("comuna")
            if raw_comuna is not None:
                try:
                    comuna_id = int(raw_comuna)
                except (ValueError, TypeError):
                    pass

        if comuna_id is None:
            logger.warning(
                "Could not determine comuna for barrio '%s', skipping.", name
            )
            continue

        geom = shape(geom_json)
        # Ensure we always store a MultiPolygon
        if geom.geom_type == "Polygon":
            geom = MultiPolygon([geom])
        elif geom.geom_type != "MultiPolygon":
            logger.warning(
                "Unexpected geometry type '%s' for %s, skipping.",
                geom.geom_type,
                name,
            )
            continue

        centroid = geom.centroid
        area_km2 = _compute_area_km2(geom)

        records.append(
            {
                "name": name,
                "slug": slugify(name),
                "comuna_id": comuna_id,
                "comuna_name": f"Comuna {comuna_id}",
                "geometry": from_shape(geom, srid=4326),
                "area_km2": round(area_km2, 4),
                "centroid_lat": round(centroid.y, 7),
                "centroid_lon": round(centroid.x, 7),
            }
        )

    return records


def build_barrio_records_fallback() -> list[dict]:
    """
    Build minimal barrio records from the embedded constant mapping.
    No geometry is available in this fallback path -- we set geometry to None.
    """
    logger.info("Using embedded fallback barrio list (no geometry).")
    records = []
    for comuna_id, names in sorted(BARRIOS_POR_COMUNA.items()):
        for name in names:
            records.append(
                {
                    "name": name,
                    "slug": slugify(name),
                    "comuna_id": comuna_id,
                    "comuna_name": f"Comuna {comuna_id}",
                    "geometry": None,
                    "area_km2": None,
                    "centroid_lat": None,
                    "centroid_lon": None,
                }
            )
    return records


def seed_barrios(force: bool = False) -> None:
    """Main seeding logic."""
    db_url = settings.sync_database_url
    logger.info("Connecting to database: %s", db_url.split("@")[-1])

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        existing_count = session.query(Barrio).count()
        if existing_count > 0 and not force:
            logger.info(
                "Barrios table already has %d records. Use --force to re-seed.",
                existing_count,
            )
            return

        if existing_count > 0 and force:
            logger.info("Force mode: deleting %d existing barrio records.", existing_count)
            session.query(Barrio).delete()
            session.commit()

        # Try sources in order: remote GeoJSON -> local GeoJSON -> fallback
        geojson = fetch_geojson()
        if geojson is None:
            geojson = load_local_geojson()

        if geojson is not None:
            records = build_barrio_records_from_geojson(geojson)
            if len(records) < 40:
                logger.warning(
                    "GeoJSON produced only %d records (expected ~48). "
                    "Falling back to embedded list.",
                    len(records),
                )
                records = build_barrio_records_fallback()
        else:
            records = build_barrio_records_fallback()

        logger.info("Inserting %d barrio records...", len(records))
        for rec in records:
            barrio = Barrio(**rec)
            session.add(barrio)

        session.commit()
        logger.info("Successfully seeded %d barrios.", len(records))

        # Quick verification
        final_count = session.query(Barrio).count()
        logger.info("Verification: barrios table now has %d rows.", final_count)

    except Exception:
        session.rollback()
        logger.exception("Error seeding barrios.")
        raise
    finally:
        session.close()
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed CABA barrios into the database."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing barrio records and re-seed.",
    )
    args = parser.parse_args()

    seed_barrios(force=args.force)


if __name__ == "__main__":
    main()
