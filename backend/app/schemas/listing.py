from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class ListingBase(BaseModel):
    """All core listing fields coming straight from the DB row."""

    id: UUID
    external_id: str
    source: str
    canonical_id: Optional[UUID] = None
    url: Optional[str] = None
    title: Optional[str] = None
    operation_type: str
    property_type: str
    price_original: Optional[Decimal] = None
    currency_original: Optional[str] = None
    price_usd_blue: Optional[Decimal] = None
    price_usd_official: Optional[Decimal] = None
    price_usd_mep: Optional[Decimal] = None
    price_ars: Optional[Decimal] = None
    expenses_ars: Optional[Decimal] = None
    surface_total_m2: Optional[Decimal] = None
    surface_covered_m2: Optional[Decimal] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    garages: Optional[int] = None
    age_years: Optional[int] = None
    amenities: Optional[dict | list] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    barrio_id: Optional[int] = None
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: Optional[bool] = True
    days_on_market: Optional[int] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Response  (list / search results)
# ---------------------------------------------------------------------------

class ListingResponse(ListingBase):
    """Listing returned in list / search endpoints, enriched with barrio name."""

    barrio_name: Optional[str] = None
    barrio_slug: Optional[str] = None
    price_usd_m2: Optional[Decimal] = Field(
        None,
        description="Computed USD/m2 based on blue rate and covered surface",
    )


# ---------------------------------------------------------------------------
# Detail  (single listing view with price history)
# ---------------------------------------------------------------------------

class PriceHistoryPoint(BaseModel):
    """A single point in a listing's price-change history."""

    date: datetime
    price_original: Optional[Decimal] = None
    currency_original: Optional[str] = None
    price_usd_blue: Optional[Decimal] = None
    source: Optional[str] = None


class ListingDetail(ListingResponse):
    """Full listing detail including historical price snapshots."""

    price_history: list[PriceHistoryPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Paginated response
# ---------------------------------------------------------------------------

class ListingsPage(BaseModel):
    """Paginated listing response."""

    items: list[ListingResponse]
    total: int = Field(ge=0, description="Total matching records")
    page: int = Field(ge=1, description="Current page number (1-based)")
    per_page: int = Field(ge=1, description="Items per page")
    pages: int = Field(ge=0, description="Total number of pages")


# ---------------------------------------------------------------------------
# Aggregated stats
# ---------------------------------------------------------------------------

class ListingStats(BaseModel):
    """Aggregated statistics for a set of listings (e.g. filtered by barrio)."""

    total_listings: int = 0
    active_listings: int = 0
    median_price_usd_m2: Optional[Decimal] = None
    avg_price_usd_m2: Optional[Decimal] = None
    min_price_usd_m2: Optional[Decimal] = None
    max_price_usd_m2: Optional[Decimal] = None
    median_surface_m2: Optional[Decimal] = None
    avg_surface_m2: Optional[Decimal] = None
    avg_days_on_market: Optional[Decimal] = None
    by_operation_type: Optional[dict[str, int]] = None
    by_property_type: Optional[dict[str, int]] = None
