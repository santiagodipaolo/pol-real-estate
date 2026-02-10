from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BarrioBase(BaseModel):
    """Minimal barrio representation used in nested / list contexts."""

    id: int
    name: str
    slug: str
    comuna_id: int
    comuna_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Geo
# ---------------------------------------------------------------------------

class BarrioGeo(BarrioBase):
    """Barrio with its geographic footprint (GeoJSON MultiPolygon)."""

    geometry: Optional[dict[str, Any]] = Field(
        None,
        description="GeoJSON geometry object (MultiPolygon)",
    )
    area_km2: Optional[Decimal] = None
    centroid_lat: Optional[Decimal] = None
    centroid_lon: Optional[Decimal] = None


# ---------------------------------------------------------------------------
# Snapshot helpers (embedded in barrio responses)
# ---------------------------------------------------------------------------

class SnapshotSummary(BaseModel):
    """Light snapshot stats embedded inside barrio responses."""

    snapshot_date: date
    operation_type: str
    property_type: Optional[str] = None
    listing_count: Optional[int] = None
    median_price_usd_m2: Optional[Decimal] = None
    avg_price_usd_m2: Optional[Decimal] = None
    p25_price_usd_m2: Optional[Decimal] = None
    p75_price_usd_m2: Optional[Decimal] = None
    avg_days_on_market: Optional[Decimal] = None
    new_listings_7d: Optional[int] = None
    removed_listings_7d: Optional[int] = None
    rental_yield_estimate: Optional[Decimal] = None
    usd_blue_rate: Optional[Decimal] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# WithStats  (barrio + latest snapshot numbers)
# ---------------------------------------------------------------------------

class BarrioWithStats(BarrioBase):
    """Barrio card with the most recent snapshot statistics."""

    listing_count: Optional[int] = None
    median_price_usd_m2: Optional[Decimal] = None
    avg_price_usd_m2: Optional[Decimal] = None
    p25_price_usd_m2: Optional[Decimal] = None
    p75_price_usd_m2: Optional[Decimal] = None
    avg_days_on_market: Optional[Decimal] = None
    rental_yield_estimate: Optional[Decimal] = None


# ---------------------------------------------------------------------------
# Detail (full info + trend history)
# ---------------------------------------------------------------------------

class BarrioDetail(BarrioGeo):
    """Full barrio detail including historical trend snapshots."""

    listing_count: Optional[int] = None
    median_price_usd_m2: Optional[Decimal] = None
    avg_price_usd_m2: Optional[Decimal] = None
    p25_price_usd_m2: Optional[Decimal] = None
    p75_price_usd_m2: Optional[Decimal] = None
    avg_days_on_market: Optional[Decimal] = None
    rental_yield_estimate: Optional[Decimal] = None
    trends: list[SnapshotSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

class BarrioRanking(BaseModel):
    """Single row returned by the ranking endpoint."""

    rank: int
    barrio_id: int
    barrio_name: str
    slug: str
    comuna_id: int
    value: Decimal = Field(description="The metric value used for ranking")
    metric: str = Field(description="Name of the metric (e.g. median_price_usd_m2)")
    listing_count: Optional[int] = None
    median_price_usd_m2: Optional[Decimal] = None
    avg_price_usd_m2: Optional[Decimal] = None
    rental_yield_estimate: Optional[Decimal] = None


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

class BarrioComparisonItem(BaseModel):
    """One barrio inside a comparison response."""

    barrio_id: int
    barrio_name: str
    slug: str
    comuna_id: int
    listing_count: Optional[int] = None
    median_price_usd_m2: Optional[Decimal] = None
    avg_price_usd_m2: Optional[Decimal] = None
    p25_price_usd_m2: Optional[Decimal] = None
    p75_price_usd_m2: Optional[Decimal] = None
    avg_days_on_market: Optional[Decimal] = None
    rental_yield_estimate: Optional[Decimal] = None
    trends: list[SnapshotSummary] = Field(default_factory=list)


class BarrioComparison(BaseModel):
    """Response for the /barrios/compare endpoint."""

    barrios: list[BarrioComparisonItem]
    generated_at: Optional[str] = None
