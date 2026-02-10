"""Barrio service — queries for neighbourhood data, snapshots, trends and
rankings."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Literal, Sequence

from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.barrio import Barrio
from app.models.barrio_snapshot import BarrioSnapshot

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────

def _latest_snapshot_subquery(operation_type: str = "sale"):
    """Return a sub-query that yields the max snapshot_date per barrio_id
    for a given operation_type."""
    return (
        select(
            BarrioSnapshot.barrio_id,
            func.max(BarrioSnapshot.snapshot_date).label("max_date"),
        )
        .where(BarrioSnapshot.operation_type == operation_type)
        .group_by(BarrioSnapshot.barrio_id)
        .subquery()
    )


# ── Public API ────────────────────────────────────────────────────────

async def get_all_barrios(db: AsyncSession) -> list[dict[str, Any]]:
    """Return every barrio together with the latest snapshot stats for each
    operation/property type combination.

    The result is a list of dicts with barrio fields and a nested
    ``latest_snapshots`` list.
    """
    latest_sub = _latest_snapshot_subquery("sale")

    # Fetch latest sale snapshots joined back to the full row
    snap_stmt = (
        select(BarrioSnapshot)
        .join(
            latest_sub,
            (BarrioSnapshot.barrio_id == latest_sub.c.barrio_id)
            & (BarrioSnapshot.snapshot_date == latest_sub.c.max_date),
        )
        .where(BarrioSnapshot.operation_type == "sale")
    )
    snap_result = await db.execute(snap_stmt)
    snapshots_by_barrio: dict[int, list[BarrioSnapshot]] = {}
    for snap in snap_result.scalars().all():
        snapshots_by_barrio.setdefault(snap.barrio_id, []).append(snap)

    # Fetch all barrios (without geometry for list view — lighter payload)
    barrio_stmt = select(Barrio).order_by(Barrio.name)
    barrio_result = await db.execute(barrio_stmt)
    barrios = barrio_result.scalars().all()

    output: list[dict[str, Any]] = []
    for b in barrios:
        snaps = snapshots_by_barrio.get(b.id, [])
        # Find the latest "sale" snapshot to flatten into the response
        sale_snap = next((s for s in snaps if s.operation_type == "sale"), None)
        entry: dict[str, Any] = {
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "comuna_id": b.comuna_id,
            "comuna_name": b.comuna_name,
            "area_km2": float(b.area_km2) if b.area_km2 else None,
            "centroid_lat": float(b.centroid_lat) if b.centroid_lat else None,
            "centroid_lon": float(b.centroid_lon) if b.centroid_lon else None,
        }
        if sale_snap:
            entry["listing_count"] = sale_snap.listing_count
            entry["median_price_usd_m2"] = float(sale_snap.median_price_usd_m2) if sale_snap.median_price_usd_m2 else None
            entry["avg_price_usd_m2"] = float(sale_snap.avg_price_usd_m2) if sale_snap.avg_price_usd_m2 else None
            entry["p25_price_usd_m2"] = float(sale_snap.p25_price_usd_m2) if sale_snap.p25_price_usd_m2 else None
            entry["p75_price_usd_m2"] = float(sale_snap.p75_price_usd_m2) if sale_snap.p75_price_usd_m2 else None
            entry["avg_days_on_market"] = float(sale_snap.avg_days_on_market) if sale_snap.avg_days_on_market else None
            entry["rental_yield_estimate"] = float(sale_snap.rental_yield_estimate) if sale_snap.rental_yield_estimate else None
        output.append(entry)
    return output


async def get_barrio_by_slug(db: AsyncSession, slug: str) -> dict[str, Any] | None:
    """Return a single barrio by its URL slug, including the 30 most recent
    snapshot rows (all operation/property types)."""
    barrio_stmt = select(Barrio).where(Barrio.slug == slug)
    barrio_result = await db.execute(barrio_stmt)
    barrio = barrio_result.scalar_one_or_none()
    if barrio is None:
        return None

    snap_stmt = (
        select(BarrioSnapshot)
        .where(BarrioSnapshot.barrio_id == barrio.id)
        .order_by(desc(BarrioSnapshot.snapshot_date))
        .limit(30)
    )
    snap_result = await db.execute(snap_stmt)
    snapshots = snap_result.scalars().all()

    # Find latest sale snapshot for flat stats
    sale_snap = next((s for s in snapshots if s.operation_type == "sale"), None)

    result: dict[str, Any] = {
        "id": barrio.id,
        "name": barrio.name,
        "slug": barrio.slug,
        "comuna_id": barrio.comuna_id,
        "comuna_name": barrio.comuna_name,
        "geometry": barrio.geometry,
        "area_km2": float(barrio.area_km2) if barrio.area_km2 else None,
        "centroid_lat": float(barrio.centroid_lat) if barrio.centroid_lat else None,
        "centroid_lon": float(barrio.centroid_lon) if barrio.centroid_lon else None,
    }

    if sale_snap:
        result["listing_count"] = sale_snap.listing_count
        result["median_price_usd_m2"] = float(sale_snap.median_price_usd_m2) if sale_snap.median_price_usd_m2 else None
        result["avg_price_usd_m2"] = float(sale_snap.avg_price_usd_m2) if sale_snap.avg_price_usd_m2 else None
        result["p25_price_usd_m2"] = float(sale_snap.p25_price_usd_m2) if sale_snap.p25_price_usd_m2 else None
        result["p75_price_usd_m2"] = float(sale_snap.p75_price_usd_m2) if sale_snap.p75_price_usd_m2 else None
        result["avg_days_on_market"] = float(sale_snap.avg_days_on_market) if sale_snap.avg_days_on_market else None
        result["rental_yield_estimate"] = float(sale_snap.rental_yield_estimate) if sale_snap.rental_yield_estimate else None

    result["trends"] = [
        {
            "snapshot_date": s.snapshot_date,
            "operation_type": s.operation_type,
            "property_type": s.property_type,
            "listing_count": s.listing_count,
            "median_price_usd_m2": float(s.median_price_usd_m2) if s.median_price_usd_m2 else None,
            "avg_price_usd_m2": float(s.avg_price_usd_m2) if s.avg_price_usd_m2 else None,
            "p25_price_usd_m2": float(s.p25_price_usd_m2) if s.p25_price_usd_m2 else None,
            "p75_price_usd_m2": float(s.p75_price_usd_m2) if s.p75_price_usd_m2 else None,
            "avg_days_on_market": float(s.avg_days_on_market) if s.avg_days_on_market else None,
            "new_listings_7d": s.new_listings_7d,
            "removed_listings_7d": s.removed_listings_7d,
            "rental_yield_estimate": float(s.rental_yield_estimate) if s.rental_yield_estimate else None,
        }
        for s in snapshots
    ]
    return result


async def get_barrio_trends(
    db: AsyncSession,
    slug: str,
    metric: str = "median_price_usd_m2",
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[dict[str, Any]]:
    """Return a time-series of *metric* values from ``barrio_snapshots``
    for the barrio identified by *slug*.

    Supported metrics correspond to numeric snapshot columns, e.g.
    ``median_price_usd_m2``, ``avg_price_usd_m2``, ``listing_count``, etc.
    """
    # Validate the metric name against known columns to prevent injection
    allowed_metrics = {
        "median_price_usd_m2",
        "avg_price_usd_m2",
        "p25_price_usd_m2",
        "p75_price_usd_m2",
        "listing_count",
        "avg_days_on_market",
        "new_listings_7d",
        "removed_listings_7d",
        "rental_yield_estimate",
    }
    if metric not in allowed_metrics:
        raise ValueError(f"Invalid metric '{metric}'. Must be one of {allowed_metrics}")

    metric_col = getattr(BarrioSnapshot, metric)

    stmt = (
        select(
            BarrioSnapshot.snapshot_date,
            BarrioSnapshot.operation_type,
            BarrioSnapshot.property_type,
            metric_col.label("value"),
        )
        .join(Barrio, Barrio.id == BarrioSnapshot.barrio_id)
        .where(Barrio.slug == slug)
    )

    if from_date:
        stmt = stmt.where(BarrioSnapshot.snapshot_date >= from_date)
    if to_date:
        stmt = stmt.where(BarrioSnapshot.snapshot_date <= to_date)

    stmt = stmt.order_by(BarrioSnapshot.snapshot_date)

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "date": row.snapshot_date.isoformat(),
            "operation_type": row.operation_type,
            "property_type": row.property_type,
            "value": float(row.value) if row.value is not None else None,
        }
        for row in rows
    ]


async def compare_barrios(
    db: AsyncSession,
    slugs: list[str],
) -> list[dict[str, Any]]:
    """Side-by-side comparison of the latest snapshot for each requested
    barrio (identified by slug)."""
    latest_sub = _latest_snapshot_subquery()

    stmt = (
        select(
            Barrio.name,
            Barrio.slug,
            BarrioSnapshot.operation_type,
            BarrioSnapshot.property_type,
            BarrioSnapshot.snapshot_date,
            BarrioSnapshot.listing_count,
            BarrioSnapshot.median_price_usd_m2,
            BarrioSnapshot.avg_price_usd_m2,
            BarrioSnapshot.p25_price_usd_m2,
            BarrioSnapshot.p75_price_usd_m2,
            BarrioSnapshot.avg_days_on_market,
            BarrioSnapshot.rental_yield_estimate,
        )
        .join(Barrio, Barrio.id == BarrioSnapshot.barrio_id)
        .join(
            latest_sub,
            (BarrioSnapshot.barrio_id == latest_sub.c.barrio_id)
            & (BarrioSnapshot.operation_type == latest_sub.c.operation_type)
            & (BarrioSnapshot.property_type == latest_sub.c.property_type)
            & (BarrioSnapshot.snapshot_date == latest_sub.c.max_date),
        )
        .where(Barrio.slug.in_(slugs))
        .order_by(Barrio.name, BarrioSnapshot.operation_type)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "name": row.name,
            "slug": row.slug,
            "operation_type": row.operation_type,
            "property_type": row.property_type,
            "snapshot_date": row.snapshot_date.isoformat() if row.snapshot_date else None,
            "listing_count": row.listing_count,
            "median_price_usd_m2": float(row.median_price_usd_m2) if row.median_price_usd_m2 else None,
            "avg_price_usd_m2": float(row.avg_price_usd_m2) if row.avg_price_usd_m2 else None,
            "p25_price_usd_m2": float(row.p25_price_usd_m2) if row.p25_price_usd_m2 else None,
            "p75_price_usd_m2": float(row.p75_price_usd_m2) if row.p75_price_usd_m2 else None,
            "avg_days_on_market": float(row.avg_days_on_market) if row.avg_days_on_market else None,
            "rental_yield_estimate": float(row.rental_yield_estimate) if row.rental_yield_estimate else None,
        }
        for row in rows
    ]


async def get_barrio_ranking(
    db: AsyncSession,
    metric: str = "median_price_usd_m2",
    operation_type: str = "venta",
    order: Literal["asc", "desc"] = "desc",
) -> list[dict[str, Any]]:
    """Return barrios ranked by *metric* from the latest snapshot, filtered
    by *operation_type*.  Only the most recent ``snapshot_date`` per barrio
    is considered."""
    allowed_metrics = {
        "median_price_usd_m2",
        "avg_price_usd_m2",
        "listing_count",
        "avg_days_on_market",
        "rental_yield_estimate",
    }
    if metric not in allowed_metrics:
        raise ValueError(f"Invalid metric '{metric}'. Must be one of {allowed_metrics}")

    metric_col = getattr(BarrioSnapshot, metric)

    # Subquery: max snapshot_date per barrio for the given operation_type
    latest_sub = (
        select(
            BarrioSnapshot.barrio_id,
            func.max(BarrioSnapshot.snapshot_date).label("max_date"),
        )
        .where(BarrioSnapshot.operation_type == operation_type)
        .group_by(BarrioSnapshot.barrio_id)
        .subquery()
    )

    order_fn = asc if order == "asc" else desc

    stmt = (
        select(
            Barrio.id.label("barrio_id"),
            Barrio.name,
            Barrio.slug,
            Barrio.comuna_id,
            metric_col.label("value"),
            BarrioSnapshot.listing_count,
            BarrioSnapshot.median_price_usd_m2,
            BarrioSnapshot.avg_price_usd_m2,
            BarrioSnapshot.rental_yield_estimate,
        )
        .join(Barrio, Barrio.id == BarrioSnapshot.barrio_id)
        .join(
            latest_sub,
            (BarrioSnapshot.barrio_id == latest_sub.c.barrio_id)
            & (BarrioSnapshot.snapshot_date == latest_sub.c.max_date),
        )
        .where(BarrioSnapshot.operation_type == operation_type)
        .where(metric_col.isnot(None))
        .order_by(order_fn(metric_col))
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "rank": idx + 1,
            "barrio_id": row.barrio_id,
            "barrio_name": row.name,
            "slug": row.slug,
            "comuna_id": row.comuna_id,
            "value": row.value,
            "metric": metric,
            "listing_count": row.listing_count,
            "median_price_usd_m2": row.median_price_usd_m2,
            "avg_price_usd_m2": row.avg_price_usd_m2,
            "rental_yield_estimate": row.rental_yield_estimate,
        }
        for idx, row in enumerate(rows)
    ]
