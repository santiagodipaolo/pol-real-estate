"""Map service — choropleth GeoJSON, heatmap points, and clustered markers."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.barrio import Barrio
from app.models.barrio_snapshot import BarrioSnapshot
from app.models.listing import Listing

logger = logging.getLogger(__name__)


# ── Choropleth ────────────────────────────────────────────────────────

async def get_choropleth_data(
    db: AsyncSession,
    metric: str = "median_price_usd_m2",
    operation_type: str = "venta",
    property_type: str | None = None,
) -> dict[str, Any]:
    """Build a GeoJSON FeatureCollection where each Feature is a barrio
    polygon, coloured by the latest snapshot *metric* value."""
    allowed_metrics = {
        "median_price_usd_m2",
        "avg_price_usd_m2",
        "listing_count",
        "avg_days_on_market",
        "rental_yield_estimate",
        "p25_price_usd_m2",
        "p75_price_usd_m2",
    }
    if metric not in allowed_metrics:
        raise ValueError(f"Invalid metric '{metric}'. Must be one of {allowed_metrics}")

    metric_col = getattr(BarrioSnapshot, metric)

    # Latest snapshot per barrio for the given operation_type
    latest_sub_q = (
        select(
            BarrioSnapshot.barrio_id,
            func.max(BarrioSnapshot.snapshot_date).label("max_date"),
        )
        .where(BarrioSnapshot.operation_type == operation_type)
    )
    if property_type:
        latest_sub_q = latest_sub_q.where(BarrioSnapshot.property_type == property_type)
    latest_sub = latest_sub_q.group_by(BarrioSnapshot.barrio_id).subquery()

    snapshot_join_cond = (
        (Barrio.id == BarrioSnapshot.barrio_id)
        & (BarrioSnapshot.operation_type == operation_type)
    )
    if property_type:
        snapshot_join_cond = snapshot_join_cond & (BarrioSnapshot.property_type == property_type)

    stmt = (
        select(
            Barrio.id,
            Barrio.name,
            Barrio.slug,
            Barrio.comuna_id,
            Barrio.comuna_name,
            Barrio.geometry,
            metric_col.label("metric_value"),
            BarrioSnapshot.listing_count,
            BarrioSnapshot.snapshot_date,
        )
        .outerjoin(
            BarrioSnapshot,
            snapshot_join_cond,
        )
        .outerjoin(
            latest_sub,
            (BarrioSnapshot.barrio_id == latest_sub.c.barrio_id)
            & (BarrioSnapshot.snapshot_date == latest_sub.c.max_date),
        )
        .where(
            (latest_sub.c.max_date.isnot(None))
            | (BarrioSnapshot.id.is_(None))
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    features: list[dict[str, Any]] = []
    for row in rows:
        geometry = row.geometry
        if geometry is None:
            continue

        feature = {
            "type": "Feature",
            "geometry": geometry,  # Already a dict from JSONB
            "properties": {
                "barrio_id": row.id,
                "barrio_name": row.name,
                "name": row.name,
                "slug": row.slug,
                "comuna_id": row.comuna_id,
                "comuna_name": row.comuna_name,
                "metric": metric,
                "value": float(row.metric_value) if row.metric_value is not None else None,
                "metric_value": float(row.metric_value) if row.metric_value is not None else None,
                "listing_count": row.listing_count,
                "snapshot_date": row.snapshot_date.isoformat() if row.snapshot_date else None,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "metric": metric,
            "operation_type": operation_type,
            "feature_count": len(features),
        },
    }


# ── Heatmap ───────────────────────────────────────────────────────────

import random
import math

async def get_heatmap_data(
    db: AsyncSession,
    operation_type: str = "sale",
    bbox: tuple[float, float, float, float] | None = None,
    property_type: str | None = None,
) -> dict[str, Any]:
    """Return dense heatmap points filling each barrio polygon."""

    # Try listing-level data first
    listing_points = await _heatmap_from_listings(db, operation_type, bbox, property_type)
    if listing_points:
        return {"points": listing_points, "metric": "price_usd_m2", "total": len(listing_points)}

    # Fallback: fill barrio polygons with points
    polygon_points = await _heatmap_from_polygons(db, operation_type, property_type)
    return {"points": polygon_points, "metric": "median_price_usd_m2", "total": len(polygon_points)}


async def _heatmap_from_listings(
    db: AsyncSession,
    operation_type: str,
    bbox: tuple[float, float, float, float] | None,
    property_type: str | None = None,
) -> list[dict[str, Any]]:
    """Build heatmap points from individual listings."""
    stmt = (
        select(
            Listing.latitude,
            Listing.longitude,
            Listing.price_usd_blue,
            Listing.surface_total_m2,
        )
        .where(
            Listing.is_active.is_(True),
            Listing.latitude.isnot(None),
            Listing.longitude.isnot(None),
            Listing.operation_type == operation_type,
        )
    )

    if property_type:
        stmt = stmt.where(Listing.property_type == property_type)

    if bbox is not None:
        min_lon, min_lat, max_lon, max_lat = bbox
        stmt = stmt.where(
            Listing.latitude >= min_lat,
            Listing.latitude <= max_lat,
            Listing.longitude >= min_lon,
            Listing.longitude <= max_lon,
        )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    points: list[dict[str, Any]] = []
    price_m2_values: list[float] = []

    for row in rows:
        price_m2 = None
        if row.price_usd_blue and row.surface_total_m2 and float(row.surface_total_m2) > 0:
            price_m2 = float(row.price_usd_blue) / float(row.surface_total_m2)
        points.append({
            "lat": float(row.latitude),
            "lon": float(row.longitude),
            "price_m2": price_m2,
        })
        if price_m2 is not None:
            price_m2_values.append(price_m2)

    return _normalize_weights(points, price_m2_values)


async def _heatmap_from_polygons(
    db: AsyncSession,
    operation_type: str,
    property_type: str | None = None,
) -> list[dict[str, Any]]:
    """Fill each barrio polygon with a dense grid of points weighted by price."""
    latest_sub_q = (
        select(
            BarrioSnapshot.barrio_id,
            func.max(BarrioSnapshot.snapshot_date).label("max_date"),
        )
        .where(BarrioSnapshot.operation_type == operation_type)
    )
    if property_type:
        latest_sub_q = latest_sub_q.where(BarrioSnapshot.property_type == property_type)
    latest_sub = latest_sub_q.group_by(BarrioSnapshot.barrio_id).subquery()

    snapshot_cond = [
        Barrio.geometry.isnot(None),
        BarrioSnapshot.operation_type == operation_type,
        BarrioSnapshot.median_price_usd_m2.isnot(None),
    ]
    if property_type:
        snapshot_cond.append(BarrioSnapshot.property_type == property_type)

    stmt = (
        select(
            Barrio.name,
            Barrio.geometry,
            Barrio.area_km2,
            BarrioSnapshot.median_price_usd_m2,
            BarrioSnapshot.listing_count,
        )
        .join(BarrioSnapshot, Barrio.id == BarrioSnapshot.barrio_id)
        .join(
            latest_sub,
            (BarrioSnapshot.barrio_id == latest_sub.c.barrio_id)
            & (BarrioSnapshot.snapshot_date == latest_sub.c.max_date),
        )
        .where(*snapshot_cond)
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    all_points: list[dict[str, Any]] = []
    all_prices: list[float] = []

    for row in rows:
        price = float(row.median_price_usd_m2)
        geometry = row.geometry
        if not geometry:
            continue

        # Determine point density based on barrio area
        area = float(row.area_km2) if row.area_km2 else 2.0
        # ~60 points per km², capped at 200 per barrio
        target_points = min(int(area * 60), 200)
        target_points = max(target_points, 30)

        barrio_points = _fill_polygon_with_points(geometry, target_points)

        for lat, lon in barrio_points:
            all_points.append({"lat": lat, "lon": lon, "price_m2": price})
            all_prices.append(price)

    return _normalize_weights(all_points, all_prices)


def _fill_polygon_with_points(
    geojson: dict[str, Any],
    target_count: int,
) -> list[tuple[float, float]]:
    """Generate evenly distributed points inside a GeoJSON polygon."""
    polygons = _extract_polygon_rings(geojson)
    if not polygons:
        return []

    # Get bounding box across all polygon rings
    all_lons: list[float] = []
    all_lats: list[float] = []
    for ring in polygons:
        for lon, lat, *_ in ring:
            all_lons.append(lon)
            all_lats.append(lat)

    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)

    width = max_lon - min_lon
    height = max_lat - min_lat
    if width <= 0 or height <= 0:
        return []

    # Calculate grid spacing to get approximately target_count points
    area = width * height
    cell_size = math.sqrt(area / (target_count * 1.8))  # 1.8 = oversampling factor
    if cell_size <= 0:
        return []

    points: list[tuple[float, float]] = []
    rng = random.Random(42)  # deterministic for caching

    lat = min_lat + cell_size * 0.5
    while lat < max_lat:
        lon = min_lon + cell_size * 0.5
        while lon < max_lon:
            # Add small jitter for natural look
            jlat = lat + rng.uniform(-cell_size * 0.3, cell_size * 0.3)
            jlon = lon + rng.uniform(-cell_size * 0.3, cell_size * 0.3)

            if _point_in_any_polygon(jlon, jlat, polygons):
                points.append((jlat, jlon))

            lon += cell_size
        lat += cell_size

    return points


def _extract_polygon_rings(geojson: dict[str, Any]) -> list[list[list[float]]]:
    """Extract outer rings from a GeoJSON Polygon or MultiPolygon."""
    geom_type = geojson.get("type", "")
    coords = geojson.get("coordinates", [])

    if geom_type == "Polygon" and coords:
        return [coords[0]]  # outer ring only
    elif geom_type == "MultiPolygon" and coords:
        return [polygon[0] for polygon in coords if polygon]
    return []


def _point_in_any_polygon(
    x: float, y: float,
    rings: list[list[list[float]]],
) -> bool:
    """Check if point (x=lon, y=lat) is inside any polygon ring."""
    return any(_point_in_ring(x, y, ring) for ring in rings)


def _point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    n = len(ring)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _normalize_weights(
    points: list[dict[str, Any]],
    price_values: list[float],
) -> list[dict[str, Any]]:
    """Normalize price_m2 values into 0.15-1.0 weights using quantile ranking.

    Quantile-based normalization guarantees a spread of weights across the
    full range even when the underlying prices have low variance.
    """
    if not price_values:
        return [
            {"lat": p["lat"], "lon": p["lon"], "weight": 0.5}
            for p in points
        ]

    # Build a sorted list of unique prices and map each to its rank percentile
    sorted_unique = sorted(set(price_values))
    n = len(sorted_unique)
    if n == 1:
        # Single unique value — everything gets mid-weight
        rank_map = {sorted_unique[0]: 0.55}
    else:
        rank_map = {
            val: i / (n - 1) for i, val in enumerate(sorted_unique)
        }

    output: list[dict[str, Any]] = []
    for p in points:
        if p["price_m2"] is not None:
            # Map rank (0-1) to weight range 0.15-1.0
            raw = rank_map.get(p["price_m2"], 0.5)
            weight = 0.15 + raw * 0.85
        else:
            weight = 0.5
        output.append({
            "lat": p["lat"],
            "lon": p["lon"],
            "weight": round(weight, 4),
        })

    return output


# ── Clusters ──────────────────────────────────────────────────────────

async def get_cluster_data(
    db: AsyncSession,
    bbox: tuple[float, float, float, float] | None = None,
    zoom: int = 12,
) -> list[dict[str, Any]]:
    """Return clustered listing points for map display."""
    cell_size = 180.0 / (2 ** zoom)

    lat_bucket = (func.floor(Listing.latitude / cell_size) * cell_size)
    lon_bucket = (func.floor(Listing.longitude / cell_size) * cell_size)

    stmt = (
        select(
            lat_bucket.label("lat_bucket"),
            lon_bucket.label("lon_bucket"),
            func.count(Listing.id).label("count"),
            func.avg(Listing.latitude).label("avg_lat"),
            func.avg(Listing.longitude).label("avg_lon"),
            func.avg(Listing.price_usd_blue).label("avg_price"),
        )
        .where(
            Listing.is_active.is_(True),
            Listing.latitude.isnot(None),
            Listing.longitude.isnot(None),
        )
        .group_by(lat_bucket, lon_bucket)
    )

    if bbox is not None:
        min_lon, min_lat, max_lon, max_lat = bbox
        stmt = stmt.where(
            Listing.latitude >= min_lat,
            Listing.latitude <= max_lat,
            Listing.longitude >= min_lon,
            Listing.longitude <= max_lon,
        )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "lat": float(row.avg_lat),
            "lon": float(row.avg_lon),
            "count": row.count,
            "avg_price_usd": round(float(row.avg_price), 2) if row.avg_price else None,
        }
        for row in rows
    ]
