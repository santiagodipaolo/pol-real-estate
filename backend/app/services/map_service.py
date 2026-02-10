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
    latest_sub = (
        select(
            BarrioSnapshot.barrio_id,
            func.max(BarrioSnapshot.snapshot_date).label("max_date"),
        )
        .where(BarrioSnapshot.operation_type == operation_type)
        .group_by(BarrioSnapshot.barrio_id)
        .subquery()
    )

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
            (Barrio.id == BarrioSnapshot.barrio_id)
            & (BarrioSnapshot.operation_type == operation_type),
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

async def get_heatmap_data(
    db: AsyncSession,
    operation_type: str = "sale",
    bbox: tuple[float, float, float, float] | None = None,
) -> dict[str, Any]:
    """Return heatmap points. Tries listing-level data first, falls back
    to barrio centroid data from snapshots."""

    # --- Try listing-level data first ---
    listing_points = await _heatmap_from_listings(db, operation_type, bbox)
    if listing_points:
        return {"points": listing_points, "metric": "price_usd_m2", "total": len(listing_points)}

    # --- Fallback: barrio centroid data from snapshots ---
    centroid_points = await _heatmap_from_snapshots(db, operation_type)
    return {"points": centroid_points, "metric": "median_price_usd_m2", "total": len(centroid_points)}


async def _heatmap_from_listings(
    db: AsyncSession,
    operation_type: str,
    bbox: tuple[float, float, float, float] | None,
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


async def _heatmap_from_snapshots(
    db: AsyncSession,
    operation_type: str,
) -> list[dict[str, Any]]:
    """Build heatmap points from barrio centroids + snapshot median price."""
    latest_sub = (
        select(
            BarrioSnapshot.barrio_id,
            func.max(BarrioSnapshot.snapshot_date).label("max_date"),
        )
        .where(BarrioSnapshot.operation_type == operation_type)
        .group_by(BarrioSnapshot.barrio_id)
        .subquery()
    )

    stmt = (
        select(
            Barrio.centroid_lat,
            Barrio.centroid_lon,
            BarrioSnapshot.median_price_usd_m2,
            BarrioSnapshot.listing_count,
        )
        .join(BarrioSnapshot, Barrio.id == BarrioSnapshot.barrio_id)
        .join(
            latest_sub,
            (BarrioSnapshot.barrio_id == latest_sub.c.barrio_id)
            & (BarrioSnapshot.snapshot_date == latest_sub.c.max_date),
        )
        .where(
            Barrio.centroid_lat.isnot(None),
            Barrio.centroid_lon.isnot(None),
            BarrioSnapshot.operation_type == operation_type,
            BarrioSnapshot.median_price_usd_m2.isnot(None),
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    points: list[dict[str, Any]] = []
    price_values: list[float] = []

    for row in rows:
        price = float(row.median_price_usd_m2)
        count = int(row.listing_count) if row.listing_count else 1
        # Create multiple points per barrio proportional to listing count
        # to make more active barrios appear more intense
        num_points = max(1, min(count // 5, 20))
        for _ in range(num_points):
            points.append({
                "lat": float(row.centroid_lat),
                "lon": float(row.centroid_lon),
                "price_m2": price,
            })
        price_values.append(price)

    return _normalize_weights(points, price_values)


def _normalize_weights(
    points: list[dict[str, Any]],
    price_values: list[float],
) -> list[dict[str, Any]]:
    """Normalize price_m2 values into 0-1 weights."""
    if price_values:
        max_val = max(price_values)
        min_val = min(price_values)
        val_range = max_val - min_val if max_val != min_val else 1.0
    else:
        min_val = 0.0
        val_range = 1.0

    output: list[dict[str, Any]] = []
    for p in points:
        weight = 0.5
        if p["price_m2"] is not None:
            weight = (p["price_m2"] - min_val) / val_range
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
