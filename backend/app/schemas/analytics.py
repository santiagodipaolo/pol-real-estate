from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Price trends
# ---------------------------------------------------------------------------

class PriceTrendPoint(BaseModel):
    """Single point on a price-trend chart."""

    date: date
    price_m2: Decimal
    currency: str = Field(
        default="USD",
        description="Currency code for the price value (USD, ARS, etc.)",
    )
    listing_count: Optional[int] = None


# ---------------------------------------------------------------------------
# Rental yield per barrio
# ---------------------------------------------------------------------------

class RentalYieldBarrio(BaseModel):
    """Rental yield metrics for one barrio."""

    barrio_id: int
    barrio_name: str
    slug: str
    median_sale_price_usd_m2: Optional[Decimal] = None
    median_rent_usd_m2: Optional[Decimal] = None
    gross_rental_yield: Optional[Decimal] = Field(
        None,
        description="Annual gross yield as a decimal (e.g. 0.045 = 4.5%)",
    )
    net_rental_yield: Optional[Decimal] = Field(
        None,
        description="Annual net yield after estimated expenses",
    )
    sale_listing_count: Optional[int] = None
    rent_listing_count: Optional[int] = None


# ---------------------------------------------------------------------------
# Market pulse (dashboard KPIs)
# ---------------------------------------------------------------------------

class MarketPulse(BaseModel):
    """High-level market health indicators."""

    active_listings: int = 0
    new_7d: int = Field(default=0, description="New listings in the last 7 days")
    removed_7d: int = Field(default=0, description="Removed listings in the last 7 days")
    avg_dom: Optional[Decimal] = Field(
        None,
        description="Average days-on-market across active listings",
    )
    median_price_usd_m2: Optional[Decimal] = None
    absorption_rate: Optional[Decimal] = Field(
        None,
        description="Monthly absorption rate (sold / active)",
    )
    snapshot_date: Optional[date] = None


# ---------------------------------------------------------------------------
# Price distribution (histogram)
# ---------------------------------------------------------------------------

class PriceDistributionStats(BaseModel):
    """Summary statistics for the distribution."""

    count: int = 0
    mean: Optional[Decimal] = None
    median: Optional[Decimal] = None
    std: Optional[Decimal] = None
    min: Optional[Decimal] = None
    max: Optional[Decimal] = None
    p25: Optional[Decimal] = None
    p75: Optional[Decimal] = None


class PriceDistribution(BaseModel):
    """Histogram data for price distribution charts."""

    bins: list[Decimal] = Field(
        default_factory=list,
        description="Left edge of each histogram bin",
    )
    counts: list[int] = Field(
        default_factory=list,
        description="Number of listings in each bin",
    )
    stats: PriceDistributionStats = Field(default_factory=PriceDistributionStats)
    currency: str = "USD"
    metric: str = Field(
        default="price_usd_m2",
        description="Which price metric was used",
    )


# ---------------------------------------------------------------------------
# ROI simulation
# ---------------------------------------------------------------------------

class ROISimulationRequest(BaseModel):
    """Input parameters for a buy-to-rent ROI simulation."""

    purchase_price_usd: Decimal = Field(description="Total purchase price in USD")
    monthly_rent_usd: Decimal = Field(description="Expected monthly rent in USD")
    monthly_expenses_usd: Decimal = Field(
        default=Decimal("0"),
        description="Monthly fixed expenses (condo fees, taxes, insurance) in USD",
    )
    vacancy_rate: Decimal = Field(
        default=Decimal("0.05"),
        description="Expected vacancy rate as a decimal (0.05 = 5%)",
    )
    annual_appreciation: Decimal = Field(
        default=Decimal("0.03"),
        description="Expected annual property appreciation as a decimal",
    )
    closing_costs_pct: Decimal = Field(
        default=Decimal("0.06"),
        description="One-time closing costs as fraction of purchase price",
    )
    holding_period_years: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Investment horizon in years",
    )
    discount_rate: Decimal = Field(
        default=Decimal("0.08"),
        description="Discount rate for NPV calculation",
    )


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

class OpportunityItem(BaseModel):
    """A listing priced below the barrio median."""

    id: str
    title: Optional[str] = None
    property_type: str
    operation_type: str
    price_usd_blue: Optional[Decimal] = None
    surface_total_m2: Optional[Decimal] = None
    price_usd_m2: Optional[Decimal] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    barrio_name: str
    barrio_slug: str
    median_price_usd_m2: Decimal
    discount_pct: Decimal = Field(description="Percentage below median (e.g. 23.5)")
    url: Optional[str] = None


class OpportunitiesResponse(BaseModel):
    """Response for the opportunities endpoint."""

    items: list[OpportunityItem]
    total: int
    avg_discount_pct: Optional[Decimal] = None
    top_barrio: Optional[str] = None


class ROISimulationResult(BaseModel):
    """Output of a buy-to-rent ROI simulation."""

    irr: Optional[Decimal] = Field(
        None,
        description="Internal rate of return (annualised) as a decimal",
    )
    npv: Optional[Decimal] = Field(
        None,
        description="Net present value in USD at the given discount rate",
    )
    payback_years: Optional[Decimal] = Field(
        None,
        description="Simple payback period in years",
    )
    cash_on_cash_return: Optional[Decimal] = Field(
        None,
        description="Year-1 cash-on-cash return as a decimal",
    )
    total_investment: Decimal = Field(
        description="Purchase price + closing costs",
    )
    annual_net_income: Decimal = Field(
        description="Year-1 net operating income",
    )
    cap_rate: Optional[Decimal] = Field(
        None,
        description="Capitalisation rate (NOI / purchase price)",
    )
    gross_rental_yield: Optional[Decimal] = Field(
        None,
        description="Annual gross rent / purchase price",
    )
