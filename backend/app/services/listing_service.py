"""Listing service — paginated listing queries and aggregate statistics."""

from __future__ import annotations

import logging
import math
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing

logger = logging.getLogger(__name__)


# ── Filter helpers ────────────────────────────────────────────────────

def _apply_filters(stmt, filters: dict[str, Any]):
    """Apply optional filters to a SQLAlchemy ``select`` statement.

    Supported keys in *filters*:
    - ``operation_type``  : exact match (e.g. "venta" / "alquiler")
    - ``property_type``   : exact match (e.g. "departamento")
    - ``barrio_id``       : exact match (int)
    - ``price_min``       : price_usd_blue >= value
    - ``price_max``       : price_usd_blue <= value
    - ``surface_min``     : surface_total_m2 >= value
    - ``surface_max``     : surface_total_m2 <= value
    - ``rooms_min``       : rooms >= value
    - ``bedrooms_min``    : bedrooms >= value
    - ``source``          : exact match
    - ``is_active``       : boolean
    """
    if not filters:
        return stmt

    if filters.get("operation_type"):
        stmt = stmt.where(Listing.operation_type == filters["operation_type"])
    if filters.get("property_type"):
        stmt = stmt.where(Listing.property_type == filters["property_type"])
    if filters.get("barrio_id") is not None:
        stmt = stmt.where(Listing.barrio_id == filters["barrio_id"])
    if filters.get("price_min") is not None:
        stmt = stmt.where(Listing.price_usd_blue >= filters["price_min"])
    if filters.get("price_max") is not None:
        stmt = stmt.where(Listing.price_usd_blue <= filters["price_max"])
    if filters.get("surface_min") is not None:
        stmt = stmt.where(Listing.surface_total_m2 >= filters["surface_min"])
    if filters.get("surface_max") is not None:
        stmt = stmt.where(Listing.surface_total_m2 <= filters["surface_max"])
    if filters.get("rooms_min") is not None:
        stmt = stmt.where(Listing.rooms >= filters["rooms_min"])
    if filters.get("bedrooms_min") is not None:
        stmt = stmt.where(Listing.bedrooms >= filters["bedrooms_min"])
    if filters.get("source"):
        stmt = stmt.where(Listing.source == filters["source"])
    if filters.get("is_active") is not None:
        stmt = stmt.where(Listing.is_active == filters["is_active"])

    return stmt


# ── Public API ────────────────────────────────────────────────────────

async def get_listings(
    db: AsyncSession,
    filters: dict[str, Any] | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """Return a paginated list of listings with optional filters.

    Returns::

        {
            "items": [ ... ],
            "total": int,
            "page": int,
            "per_page": int,
            "pages": int,
        }
    """
    filters = filters or {}

    # Total count
    count_stmt = select(func.count()).select_from(Listing)
    count_stmt = _apply_filters(count_stmt, filters)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Paginated data
    offset = (page - 1) * per_page
    data_stmt = (
        select(Listing)
        .order_by(Listing.last_seen_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    data_stmt = _apply_filters(data_stmt, filters)

    result = await db.execute(data_stmt)
    listings = result.scalars().all()

    return {
        "items": [_listing_to_dict(l) for l in listings],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if per_page else 0,
    }


async def get_listing_by_id(db: AsyncSession, listing_id: UUID) -> dict[str, Any] | None:
    """Fetch a single listing by its UUID primary key."""
    stmt = select(Listing).where(Listing.id == listing_id)
    result = await db.execute(stmt)
    listing = result.scalar_one_or_none()
    if listing is None:
        return None
    return _listing_to_dict(listing)


async def get_listing_stats(
    db: AsyncSession,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return aggregated statistics for listings matching *filters*.

    Statistics include count, average / min / max price, and a rough
    approximation of the median via ``percentile_cont``.
    """
    filters = filters or {}

    base_stmt = select(
        func.count(Listing.id).label("count"),
        func.avg(Listing.price_usd_blue).label("avg_price"),
        func.min(Listing.price_usd_blue).label("min_price"),
        func.max(Listing.price_usd_blue).label("max_price"),
        func.avg(Listing.surface_total_m2).label("avg_surface"),
        func.avg(Listing.days_on_market).label("avg_days_on_market"),
    )
    base_stmt = _apply_filters(base_stmt, filters)

    result = await db.execute(base_stmt)
    row = result.one()

    # Median via percentile_cont (PostgreSQL-specific)
    median_stmt = select(
        func.percentile_cont(0.5).within_group(Listing.price_usd_blue).label("median_price"),
    ).select_from(Listing)
    median_stmt = _apply_filters(median_stmt, filters)

    median_result = await db.execute(median_stmt)
    median_row = median_result.one()

    # Price per m2 stats (only where both price and surface are present)
    price_m2_expr = Listing.price_usd_blue / Listing.surface_total_m2
    price_m2_stmt = select(
        func.avg(price_m2_expr).label("avg_price_m2"),
        func.percentile_cont(0.5).within_group(price_m2_expr).label("median_price_m2"),
    ).select_from(Listing).where(
        Listing.price_usd_blue.isnot(None),
        Listing.surface_total_m2.isnot(None),
        Listing.surface_total_m2 > 0,
    )
    price_m2_stmt = _apply_filters(price_m2_stmt, filters)

    price_m2_result = await db.execute(price_m2_stmt)
    price_m2_row = price_m2_result.one()

    return {
        "count": row.count,
        "avg_price": _to_float(row.avg_price),
        "min_price": _to_float(row.min_price),
        "max_price": _to_float(row.max_price),
        "median_price": _to_float(median_row.median_price),
        "avg_surface_m2": _to_float(row.avg_surface),
        "avg_days_on_market": _to_float(row.avg_days_on_market),
        "avg_price_usd_m2": _to_float(price_m2_row.avg_price_m2),
        "median_price_usd_m2": _to_float(price_m2_row.median_price_m2),
    }


# ── Internal helpers ──────────────────────────────────────────────────

def _to_float(value) -> float | None:
    """Safely convert a decimal/numeric DB value to float."""
    if value is None:
        return None
    return float(value)


def _listing_to_dict(listing: Listing) -> dict[str, Any]:
    """Convert a :class:`Listing` ORM instance to a plain dict."""
    return {
        "id": str(listing.id),
        "external_id": listing.external_id,
        "source": listing.source,
        "url": listing.url,
        "title": listing.title,
        "operation_type": listing.operation_type,
        "property_type": listing.property_type,
        "price_original": _to_float(listing.price_original),
        "currency_original": listing.currency_original,
        "price_usd_blue": _to_float(listing.price_usd_blue),
        "price_usd_official": _to_float(listing.price_usd_official),
        "price_usd_mep": _to_float(listing.price_usd_mep),
        "price_ars": _to_float(listing.price_ars),
        "expenses_ars": _to_float(listing.expenses_ars),
        "surface_total_m2": _to_float(listing.surface_total_m2),
        "surface_covered_m2": _to_float(listing.surface_covered_m2),
        "rooms": listing.rooms,
        "bedrooms": listing.bedrooms,
        "bathrooms": listing.bathrooms,
        "garages": listing.garages,
        "age_years": listing.age_years,
        "amenities": listing.amenities,
        "latitude": _to_float(listing.latitude),
        "longitude": _to_float(listing.longitude),
        "barrio_id": listing.barrio_id,
        "is_active": listing.is_active,
        "days_on_market": listing.days_on_market,
        "first_seen_at": listing.first_seen_at.isoformat() if listing.first_seen_at else None,
        "last_seen_at": listing.last_seen_at.isoformat() if listing.last_seen_at else None,
    }
