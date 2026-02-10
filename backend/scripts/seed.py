"""Seed script — Barrios + Listings + Snapshots + CurrencyRate.

Usage:
    cd backend
    python -m scripts.seed
"""

from __future__ import annotations

import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Append parent so we can import app modules when running with `python -m`
sys.path.insert(0, ".")

from app.core.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BARRIOS_GEOJSON_URL = (
    "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
    "ministerio-de-educacion/barrios/barrios.geojson"
)

BLUE_RATE_BUY = 1180.0
BLUE_RATE_SELL = 1200.0

LISTINGS_PER_BARRIO = (60, 80)
SNAPSHOT_WEEKS = 24  # 6 months of weekly snapshots

# Sale price USD/m2 ranges per barrio
PRICE_RANGES: dict[str, tuple[int, int]] = {
    "Puerto Madero": (4500, 6500),
    "Palermo": (2800, 3800),
    "Recoleta": (2600, 3600),
    "Belgrano": (2400, 3200),
    "Núñez": (2200, 3000),
    "Nuñez": (2200, 3000),
    "Caballito": (1800, 2600),
    "Villa Urquiza": (1900, 2600),
    "Villa Crespo": (1800, 2400),
    "Almagro": (1600, 2200),
    "Flores": (1200, 1800),
    "La Boca": (900, 1500),
    "Villa Lugano": (600, 1000),
}
DEFAULT_PRICE_RANGE = (1200, 2000)

RENT_YIELD_MONTHLY = 0.004  # ~5% annual

PROPERTY_TYPES = ["Departamento", "Casa", "PH"]
PROPERTY_WEIGHTS = [0.70, 0.15, 0.15]

SOURCES = ["zonaprop", "argenprop", "mercadolibre"]

random.seed(42)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify(name: str) -> str:
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_str.lower().replace(" ", "-")


def compute_centroid(geometry: dict) -> tuple[float, float]:
    """Compute a simple centroid (average of all coordinates)."""
    coords = geometry.get("coordinates", [])
    geo_type = geometry.get("type", "")

    all_points: list[tuple[float, float]] = []

    def _extract(c, depth: int):
        if depth == 0:
            all_points.append((c[0], c[1]))
        else:
            for item in c:
                _extract(item, depth - 1)

    if geo_type == "Polygon":
        _extract(coords, 2)
    elif geo_type == "MultiPolygon":
        _extract(coords, 3)
    else:
        _extract(coords, 2)

    if not all_points:
        return (0.0, 0.0)

    avg_lon = sum(p[0] for p in all_points) / len(all_points)
    avg_lat = sum(p[1] for p in all_points) / len(all_points)
    return (avg_lat, avg_lon)


def bounding_box(geometry: dict) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) for a geometry."""
    all_points: list[tuple[float, float]] = []

    def _extract(c, depth: int):
        if depth == 0:
            all_points.append((c[0], c[1]))
        else:
            for item in c:
                _extract(item, depth - 1)

    geo_type = geometry.get("type", "")
    coords = geometry.get("coordinates", [])

    if geo_type == "Polygon":
        _extract(coords, 2)
    elif geo_type == "MultiPolygon":
        _extract(coords, 3)
    else:
        _extract(coords, 2)

    lons = [p[0] for p in all_points]
    lats = [p[1] for p in all_points]
    return (min(lons), min(lats), max(lons), max(lats))


def random_point_in_bbox(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float
) -> tuple[float, float]:
    """Return a random (lat, lon) within the bounding box."""
    lat = random.uniform(min_lat, max_lat)
    lon = random.uniform(min_lon, max_lon)
    return (lat, lon)


def get_price_range(barrio_name: str) -> tuple[int, int]:
    return PRICE_RANGES.get(barrio_name, DEFAULT_PRICE_RANGE)


# ---------------------------------------------------------------------------
# 1. Fetch barrios GeoJSON
# ---------------------------------------------------------------------------


def fetch_barrios_geojson() -> list[dict]:
    print("Fetching barrios GeoJSON from Buenos Aires open data...")
    resp = httpx.get(BARRIOS_GEOJSON_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features", [])
    print(f"  -> Got {len(features)} features")
    return features


# ---------------------------------------------------------------------------
# 2. Insert barrios
# ---------------------------------------------------------------------------


def seed_barrios(session: Session, features: list[dict]) -> dict[str, int]:
    """Insert barrios using ON CONFLICT upsert. Returns {name: id} mapping."""
    print("Seeding barrios...")
    name_to_id: dict[str, int] = {}

    for feat in features:
        props = feat.get("properties", {})
        geometry = feat.get("geometry", {})

        name = props.get("BARRIO") or props.get("nombre", "")
        name = name.strip().title()
        if not name:
            continue

        comuna_raw = props.get("COMUNA") or props.get("comuna", 0)
        try:
            comuna_id = int(comuna_raw)
        except (ValueError, TypeError):
            comuna_id = 0

        area_raw = props.get("AREA") or props.get("area_metro") or props.get("AREA_KM2", 0)
        try:
            area_m2 = float(area_raw)
        except (ValueError, TypeError):
            area_m2 = 0.0
        # If it's in m2, convert to km2
        area_km2 = area_m2 / 1_000_000 if area_m2 > 1000 else area_m2

        centroid_lat, centroid_lon = compute_centroid(geometry)
        slug = slugify(name)

        session.execute(
            text("""
                INSERT INTO barrios (name, slug, comuna_id, comuna_name, geometry, area_km2, centroid_lat, centroid_lon)
                VALUES (:name, :slug, :comuna_id, :comuna_name, CAST(:geometry AS jsonb), :area_km2, :centroid_lat, :centroid_lon)
                ON CONFLICT (name) DO UPDATE SET
                    slug = EXCLUDED.slug,
                    comuna_id = EXCLUDED.comuna_id,
                    comuna_name = EXCLUDED.comuna_name,
                    geometry = EXCLUDED.geometry,
                    area_km2 = EXCLUDED.area_km2,
                    centroid_lat = EXCLUDED.centroid_lat,
                    centroid_lon = EXCLUDED.centroid_lon
            """),
            {
                "name": name,
                "slug": slug,
                "comuna_id": comuna_id,
                "comuna_name": f"Comuna {comuna_id}",
                "geometry": json.dumps(geometry),
                "area_km2": round(area_km2, 4),
                "centroid_lat": round(centroid_lat, 7),
                "centroid_lon": round(centroid_lon, 7),
            },
        )

    session.commit()

    # Fetch back IDs
    rows = session.execute(text("SELECT id, name FROM barrios")).fetchall()
    for row in rows:
        name_to_id[row[1]] = row[0]

    print(f"  -> {len(name_to_id)} barrios in DB")
    return name_to_id


# ---------------------------------------------------------------------------
# 3. Generate listings
# ---------------------------------------------------------------------------


def generate_listings(
    barrio_name: str,
    barrio_id: int,
    geometry: dict,
    now: datetime,
) -> list[dict]:
    """Generate synthetic listings for one barrio."""
    bbox = bounding_box(geometry)
    sale_min, sale_max = get_price_range(barrio_name)
    count = random.randint(*LISTINGS_PER_BARRIO)
    listings = []

    for _ in range(count):
        # 60% sale, 40% rent
        is_sale = random.random() < 0.60
        operation_type = "sale" if is_sale else "rent"

        prop_type = random.choices(PROPERTY_TYPES, PROPERTY_WEIGHTS, k=1)[0]
        surface = round(random.uniform(30, 150), 2)
        rooms = random.randint(1, 5)
        bedrooms = min(rooms, random.randint(1, 4))
        bathrooms = random.randint(1, max(1, bedrooms))

        sale_price_m2 = random.uniform(sale_min, sale_max)

        if is_sale:
            price_usd = round(sale_price_m2 * surface, 2)
            price_ars = round(price_usd * BLUE_RATE_SELL, 2)
            currency = "USD"
        else:
            monthly_rent_usd = round(sale_price_m2 * RENT_YIELD_MONTHLY * surface, 2)
            price_usd = monthly_rent_usd
            price_ars = round(monthly_rent_usd * BLUE_RATE_SELL, 2)
            currency = "ARS"

        # Stagger first_seen_at over 6 months
        days_ago = random.randint(0, 180)
        first_seen = now - timedelta(days=days_ago)
        dom = days_ago  # days on market

        lat, lon = random_point_in_bbox(*bbox)
        source = random.choice(SOURCES)
        ext_id = f"{source}-{uuid.uuid4().hex[:12]}"

        listings.append(
            {
                "id": str(uuid.uuid4()),
                "external_id": ext_id,
                "source": source,
                "url": f"https://{source}.com.ar/propiedades/{ext_id}",
                "title": f"{prop_type} en {operation_type} - {barrio_name}",
                "operation_type": operation_type,
                "property_type": prop_type,
                "price_original": price_ars if currency == "ARS" else price_usd,
                "currency_original": currency,
                "price_usd_blue": price_usd,
                "price_ars": price_ars,
                "surface_total_m2": surface,
                "surface_covered_m2": round(surface * random.uniform(0.85, 1.0), 2),
                "rooms": rooms,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "garages": random.choice([0, 0, 0, 1, 1, 2]),
                "latitude": round(lat, 7),
                "longitude": round(lon, 7),
                "barrio_id": barrio_id,
                "first_seen_at": first_seen.isoformat(),
                "last_seen_at": now.isoformat(),
                "is_active": True,
                "days_on_market": dom,
            }
        )

    return listings


def seed_listings(
    session: Session,
    name_to_id: dict[str, int],
    features: list[dict],
    now: datetime,
) -> int:
    """Generate and insert listings for all barrios. Returns total count."""
    print("Clearing existing listings...")
    session.execute(text("DELETE FROM listings"))
    session.commit()

    # Build geometry lookup by name
    geo_by_name: dict[str, dict] = {}
    for feat in features:
        props = feat.get("properties", {})
        name = (props.get("BARRIO") or props.get("nombre", "")).strip().title()
        geo_by_name[name] = feat.get("geometry", {})

    total = 0
    print("Generating listings...")
    for barrio_name, barrio_id in sorted(name_to_id.items()):
        geometry = geo_by_name.get(barrio_name, {})
        if not geometry:
            continue

        batch = generate_listings(barrio_name, barrio_id, geometry, now)
        if not batch:
            continue

        session.execute(
            text("""
                INSERT INTO listings (
                    id, external_id, source, url, title, operation_type, property_type,
                    price_original, currency_original, price_usd_blue, price_ars,
                    surface_total_m2, surface_covered_m2,
                    rooms, bedrooms, bathrooms, garages,
                    latitude, longitude, barrio_id,
                    first_seen_at, last_seen_at, is_active, days_on_market
                ) VALUES (
                    CAST(:id AS uuid), :external_id, :source, :url, :title,
                    :operation_type, :property_type,
                    :price_original, :currency_original, :price_usd_blue, :price_ars,
                    :surface_total_m2, :surface_covered_m2,
                    :rooms, :bedrooms, :bathrooms, :garages,
                    :latitude, :longitude, :barrio_id,
                    CAST(:first_seen_at AS timestamptz),
                    CAST(:last_seen_at AS timestamptz),
                    :is_active, :days_on_market
                )
            """),
            batch,
        )
        total += len(batch)
        print(f"  {barrio_name}: {len(batch)} listings")

    session.commit()
    print(f"  -> Total: {total} listings")
    return total


# ---------------------------------------------------------------------------
# 4. Compute snapshots
# ---------------------------------------------------------------------------


def compute_percentiles(values: list[float]) -> dict:
    """Compute median, avg, p25, p75 from a list of floats."""
    if not values:
        return {
            "median": None,
            "avg": None,
            "p25": None,
            "p75": None,
        }
    s = sorted(values)
    n = len(s)

    def percentile(pct: float) -> float:
        idx = pct * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return s[lo] + frac * (s[hi] - s[lo])

    return {
        "median": round(percentile(0.50), 2),
        "avg": round(sum(s) / n, 2),
        "p25": round(percentile(0.25), 2),
        "p75": round(percentile(0.75), 2),
    }


def seed_snapshots(session: Session, name_to_id: dict[str, int], now: datetime) -> int:
    """Generate weekly snapshots for the past 6 months."""
    print("Clearing existing snapshots...")
    session.execute(text("DELETE FROM barrio_snapshots"))
    session.commit()

    print("Computing snapshots...")
    today = now.date()
    snapshot_dates = [today - timedelta(weeks=w) for w in range(SNAPSHOT_WEEKS)]
    snapshot_dates.reverse()  # oldest first

    # Fetch all listings for computation
    rows = session.execute(
        text("""
            SELECT barrio_id, operation_type, price_usd_blue,
                   surface_covered_m2, days_on_market, first_seen_at
            FROM listings
            WHERE is_active = true
              AND price_usd_blue IS NOT NULL
              AND surface_covered_m2 IS NOT NULL
              AND surface_covered_m2 > 0
        """)
    ).fetchall()

    # Group by (barrio_id, operation_type)
    groups: dict[tuple[int, str], list[dict]] = {}
    for r in rows:
        key = (r[0], r[1])
        groups.setdefault(key, []).append(
            {
                "price_m2": float(r[2]) / float(r[3]),
                "dom": r[4] or 0,
                "first_seen": r[5],
            }
        )

    total = 0
    batch = []

    for (barrio_id, op_type), listings in sorted(groups.items()):
        base_prices = [l["price_m2"] for l in listings]

        for i, snap_date in enumerate(snapshot_dates):
            # Apply slight price drift: +0.5%/month from oldest snapshot
            months_from_start = i * 7 / 30  # weeks * 7 / 30
            drift = 1.0 + 0.005 * months_from_start
            adjusted = [p * drift for p in base_prices]

            stats = compute_percentiles(adjusted)
            avg_dom = round(sum(l["dom"] for l in listings) / len(listings), 1)

            # Simulate new/removed listings for each week
            new_7d = random.randint(0, max(1, len(listings) // 10))
            removed_7d = random.randint(0, max(1, len(listings) // 15))

            batch.append(
                {
                    "barrio_id": barrio_id,
                    "snapshot_date": snap_date.isoformat(),
                    "operation_type": op_type,
                    "property_type": None,
                    "listing_count": len(listings),
                    "median_price_usd_m2": stats["median"],
                    "avg_price_usd_m2": stats["avg"],
                    "p25_price_usd_m2": stats["p25"],
                    "p75_price_usd_m2": stats["p75"],
                    "avg_days_on_market": avg_dom,
                    "new_listings_7d": new_7d,
                    "removed_listings_7d": removed_7d,
                    "usd_blue_rate": BLUE_RATE_SELL,
                }
            )
            total += 1

    # Bulk insert in chunks of 500
    for chunk_start in range(0, len(batch), 500):
        chunk = batch[chunk_start : chunk_start + 500]
        session.execute(
            text("""
                INSERT INTO barrio_snapshots (
                    barrio_id, snapshot_date, operation_type, property_type,
                    listing_count, median_price_usd_m2, avg_price_usd_m2,
                    p25_price_usd_m2, p75_price_usd_m2, avg_days_on_market,
                    new_listings_7d, removed_listings_7d, usd_blue_rate
                ) VALUES (
                    :barrio_id, CAST(:snapshot_date AS date), :operation_type,
                    :property_type,
                    :listing_count, :median_price_usd_m2, :avg_price_usd_m2,
                    :p25_price_usd_m2, :p75_price_usd_m2, :avg_days_on_market,
                    :new_listings_7d, :removed_listings_7d, :usd_blue_rate
                )
            """),
            chunk,
        )

    session.commit()
    print(f"  -> {total} snapshots across {len(groups)} groups x {SNAPSHOT_WEEKS} weeks")
    return total


# ---------------------------------------------------------------------------
# 5. Seed currency rate
# ---------------------------------------------------------------------------


def seed_currency_rate(session: Session, now: datetime):
    print("Seeding currency rate (blue dollar)...")
    session.execute(
        text("""
            INSERT INTO currency_rates (rate_type, buy, sell, source, recorded_at)
            VALUES (:rate_type, :buy, :sell, :source, CAST(:recorded_at AS timestamptz))
        """),
        {
            "rate_type": "blue",
            "buy": BLUE_RATE_BUY,
            "sell": BLUE_RATE_SELL,
            "source": "seed",
            "recorded_at": now.isoformat(),
        },
    )
    session.commit()
    print(f"  -> Blue: buy={BLUE_RATE_BUY}, sell={BLUE_RATE_SELL}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("POL Real Estate — Database Seed Script")
    print("=" * 60)

    db_url = settings.sync_database_url
    # Mask password in output
    display_url = db_url
    if "@" in display_url:
        pre, post = display_url.split("@", 1)
        if ":" in pre:
            scheme_user = pre.rsplit(":", 1)[0]
            display_url = f"{scheme_user}:***@{post}"
    print(f"Database: {display_url}")
    print()

    engine = create_engine(db_url)
    now = datetime.now(timezone.utc)

    try:
        with Session(engine) as session:
            # 1. Fetch and seed barrios
            features = fetch_barrios_geojson()
            name_to_id = seed_barrios(session, features)

            # 2. Generate and insert listings
            seed_listings(session, name_to_id, features, now)

            # 3. Compute and insert snapshots
            seed_snapshots(session, name_to_id, now)

            # 4. Seed currency rate
            seed_currency_rate(session, now)

        print()
        print("=" * 60)
        print("Seed complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
