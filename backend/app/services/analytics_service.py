"""Analytics service — price trends, rental yields, market pulse,
price distributions, and ROI simulation."""

from __future__ import annotations

import logging
import math
from typing import Any

from sqlalchemy import select, func, desc, case, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.barrio import Barrio
from app.models.barrio_snapshot import BarrioSnapshot
from app.models.listing import Listing

logger = logging.getLogger(__name__)


# ── Price trends ──────────────────────────────────────────────────────

async def get_price_trends(
    db: AsyncSession,
    operation_type: str = "sale",
    currency: str = "usd",
    inflation_adjusted: bool = False,
) -> list[dict[str, Any]]:
    """Return city-wide price-per-m2 time-series from barrio snapshots.

    When *inflation_adjusted* is ``True`` and the snapshot stores the
    ``usd_blue_rate`` at snapshot time, we normalize values to the most
    recent blue rate so that all observations are in "today's USD".
    """
    # Average across all barrios per snapshot_date
    stmt = (
        select(
            BarrioSnapshot.snapshot_date,
            func.avg(BarrioSnapshot.median_price_usd_m2).label("avg_median_price_m2"),
            func.avg(BarrioSnapshot.avg_price_usd_m2).label("avg_avg_price_m2"),
            func.sum(BarrioSnapshot.listing_count).label("total_listings"),
            func.avg(BarrioSnapshot.usd_blue_rate).label("avg_blue_rate"),
        )
        .where(BarrioSnapshot.operation_type == operation_type)
        .group_by(BarrioSnapshot.snapshot_date)
        .order_by(BarrioSnapshot.snapshot_date)
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    # For inflation adjustment, use the most recent rate as the base
    latest_rate = None
    if inflation_adjusted:
        for row in reversed(rows):
            if row.avg_blue_rate and float(row.avg_blue_rate) > 0:
                latest_rate = float(row.avg_blue_rate)
                break

    output: list[dict[str, Any]] = []
    for row in rows:
        median_val = float(row.avg_median_price_m2) if row.avg_median_price_m2 else None
        avg_val = float(row.avg_avg_price_m2) if row.avg_avg_price_m2 else None
        blue_rate = float(row.avg_blue_rate) if row.avg_blue_rate else None

        if inflation_adjusted and latest_rate and blue_rate and blue_rate > 0:
            # Adjust: if blue rate was lower in the past, the USD was
            # "worth more" in ARS terms, so the real USD price was higher.
            adjustment_factor = blue_rate / latest_rate
            if median_val is not None:
                median_val = median_val * adjustment_factor
            if avg_val is not None:
                avg_val = avg_val * adjustment_factor

        output.append({
            "date": row.snapshot_date.isoformat(),
            "price_m2": round(median_val, 2) if median_val else 0,
            "currency": currency,
            "listing_count": row.total_listings,
        })

    return output


# ── Rental yield ──────────────────────────────────────────────────────

async def get_rental_yield(db: AsyncSession) -> list[dict[str, Any]]:
    """Compute the gross rental yield per barrio.

    Yield = (monthly_rent * 12) / sale_price, expressed as a percentage.
    We use the latest snapshots for both ``alquiler`` and ``venta`` and
    compare their median price/m2 values.
    """
    # Latest snapshot per barrio per operation_type
    latest_sub = (
        select(
            BarrioSnapshot.barrio_id,
            BarrioSnapshot.operation_type,
            func.max(BarrioSnapshot.snapshot_date).label("max_date"),
        )
        .group_by(BarrioSnapshot.barrio_id, BarrioSnapshot.operation_type)
        .subquery()
    )

    snap_stmt = (
        select(
            BarrioSnapshot.barrio_id,
            BarrioSnapshot.operation_type,
            BarrioSnapshot.median_price_usd_m2,
            BarrioSnapshot.rental_yield_estimate,
        )
        .join(
            latest_sub,
            (BarrioSnapshot.barrio_id == latest_sub.c.barrio_id)
            & (BarrioSnapshot.operation_type == latest_sub.c.operation_type)
            & (BarrioSnapshot.snapshot_date == latest_sub.c.max_date),
        )
        .where(BarrioSnapshot.operation_type.in_(["sale", "rent"]))
    )

    result = await db.execute(snap_stmt)
    rows = result.all()

    # Pivot by barrio_id
    data_by_barrio: dict[int, dict[str, Any]] = {}
    for row in rows:
        entry = data_by_barrio.setdefault(row.barrio_id, {"barrio_id": row.barrio_id})
        if row.operation_type == "sale":
            entry["sale_price_m2"] = float(row.median_price_usd_m2) if row.median_price_usd_m2 else None
        elif row.operation_type == "rent":
            entry["rent_price_m2"] = float(row.median_price_usd_m2) if row.median_price_usd_m2 else None
        if row.rental_yield_estimate is not None:
            entry["precomputed_yield"] = float(row.rental_yield_estimate)

    # Fetch barrio names
    barrio_ids = list(data_by_barrio.keys())
    if barrio_ids:
        barrio_stmt = select(Barrio.id, Barrio.name, Barrio.slug).where(Barrio.id.in_(barrio_ids))
        barrio_result = await db.execute(barrio_stmt)
        for b_row in barrio_result.all():
            if b_row.id in data_by_barrio:
                data_by_barrio[b_row.id]["name"] = b_row.name
                data_by_barrio[b_row.id]["slug"] = b_row.slug

    output: list[dict[str, Any]] = []
    for entry in data_by_barrio.values():
        sale = entry.get("sale_price_m2")
        rent = entry.get("rent_price_m2")

        # Compute yield: (monthly_rent_per_m2 * 12) / sale_price_per_m2 * 100
        gross_yield = None
        net_yield = None
        if sale and rent and sale > 0:
            gross_yield = round((rent * 12) / sale * 100, 2)
            # Net yield assumes ~30% expenses on rent
            net_yield = round((rent * 12 * 0.7) / sale * 100, 2)

        output.append({
            "barrio_id": entry["barrio_id"],
            "barrio_name": entry.get("name"),
            "slug": entry.get("slug"),
            "median_sale_price_usd_m2": sale,
            "median_rent_usd_m2": rent,
            "gross_rental_yield": gross_yield,
            "net_rental_yield": net_yield,
        })

    # Sort by yield descending
    output.sort(key=lambda x: x.get("gross_rental_yield") or 0, reverse=True)
    return output


# ── Market pulse ──────────────────────────────────────────────────────

async def get_market_pulse(db: AsyncSession) -> dict[str, Any]:
    """High-level market activity metrics from snapshots and listings."""
    # Latest snapshot date
    latest_date_stmt = select(func.max(BarrioSnapshot.snapshot_date))
    latest_date_result = await db.execute(latest_date_stmt)
    latest_date = latest_date_result.scalar_one_or_none()

    active_listings = 0
    new_7d = 0
    removed_7d = 0
    avg_dom = None
    median_price = None
    absorption_rate = None

    if latest_date:
        # Aggregate from latest sale snapshots
        pulse_stmt = select(
            func.sum(BarrioSnapshot.listing_count).label("total_listings"),
            func.sum(BarrioSnapshot.new_listings_7d).label("new_7d"),
            func.sum(BarrioSnapshot.removed_listings_7d).label("removed_7d"),
            func.avg(BarrioSnapshot.avg_days_on_market).label("avg_dom"),
            func.avg(BarrioSnapshot.median_price_usd_m2).label("median_price"),
        ).where(
            BarrioSnapshot.snapshot_date == latest_date,
            BarrioSnapshot.operation_type == "sale",
        )

        pulse_result = await db.execute(pulse_stmt)
        pulse_row = pulse_result.one()

        active_listings = pulse_row.total_listings or 0
        new_7d = pulse_row.new_7d or 0
        removed_7d = pulse_row.removed_7d or 0
        avg_dom = round(float(pulse_row.avg_dom), 1) if pulse_row.avg_dom else None
        median_price = round(float(pulse_row.median_price), 2) if pulse_row.median_price else None

        if active_listings and removed_7d:
            absorption_rate = round(removed_7d / active_listings * 100, 2)

    return {
        "active_listings": active_listings,
        "new_7d": new_7d,
        "removed_7d": removed_7d,
        "avg_dom": avg_dom,
        "median_price_usd_m2": median_price,
        "absorption_rate": absorption_rate,
        "snapshot_date": latest_date.isoformat() if latest_date else None,
    }


# ── Price distribution ────────────────────────────────────────────────

async def get_price_distribution(
    db: AsyncSession,
    barrio_id: int | None = None,
    bins: int = 20,
) -> dict[str, Any]:
    """Build histogram data for price_usd_blue distribution.

    Returns bin edges and counts suitable for front-end charting.
    """
    # Get min/max price for bin calculation
    range_stmt = select(
        func.min(Listing.price_usd_blue).label("min_price"),
        func.max(Listing.price_usd_blue).label("max_price"),
        func.count(Listing.id).label("total"),
    ).where(
        Listing.is_active.is_(True),
        Listing.price_usd_blue.isnot(None),
        Listing.price_usd_blue > 0,
    )
    if barrio_id is not None:
        range_stmt = range_stmt.where(Listing.barrio_id == barrio_id)

    range_result = await db.execute(range_stmt)
    range_row = range_result.one()

    if not range_row.min_price or not range_row.max_price or range_row.total == 0:
        return {"bins": [], "total": 0}

    min_price = float(range_row.min_price)
    max_price = float(range_row.max_price)
    total = range_row.total

    bin_width = (max_price - min_price) / bins
    if bin_width <= 0:
        return {
            "bins": [{"lower": min_price, "upper": max_price, "count": total}],
            "total": total,
        }

    # Use PostgreSQL width_bucket to assign each listing to a bin
    bucket_expr = func.width_bucket(
        Listing.price_usd_blue, min_price, max_price + 0.01, bins
    )

    hist_stmt = (
        select(
            bucket_expr.label("bucket"),
            func.count().label("count"),
        )
        .where(
            Listing.is_active.is_(True),
            Listing.price_usd_blue.isnot(None),
            Listing.price_usd_blue > 0,
        )
        .group_by(bucket_expr)
        .order_by(bucket_expr)
    )
    if barrio_id is not None:
        hist_stmt = hist_stmt.where(Listing.barrio_id == barrio_id)

    hist_result = await db.execute(hist_stmt)
    hist_rows = hist_result.all()

    # Build the output bins
    bin_data: list[dict[str, Any]] = []
    bucket_map = {row.bucket: row.count for row in hist_rows}
    for i in range(1, bins + 1):
        lower = min_price + (i - 1) * bin_width
        upper = min_price + i * bin_width
        bin_data.append({
            "lower": round(lower, 2),
            "upper": round(upper, 2),
            "count": bucket_map.get(i, 0),
        })

    return {
        "bins": bin_data,
        "total": total,
        "bin_width": round(bin_width, 2),
    }


# ── ROI Simulation ───────────────────────────────────────────────────

async def simulate_roi(params: dict[str, Any]) -> dict[str, Any]:
    """Run a buy-to-rent ROI simulation.

    Expected *params*::

        {
            "purchase_price_usd": float,    # total purchase price
            "monthly_rent_usd": float,      # expected monthly rent
            "holding_period_years": int,     # investment horizon
            "annual_appreciation_pct": float,  # e.g. 3.0 for 3%
            "annual_expenses_pct": float,    # annual costs as % of price (e.g. 2.0)
            "vacancy_rate_pct": float,       # e.g. 5.0 for 5%
            "closing_costs_pct": float,      # buy/sell transaction costs
            "annual_rent_increase_pct": float,  # annual rent escalation
        }

    Returns IRR, NPV, total return, and year-by-year cash flow breakdown.
    """
    purchase_price = float(params.get("purchase_price_usd", 0))
    monthly_rent = float(params.get("monthly_rent_usd", 0))
    years = int(params.get("holding_period_years", 10))
    appreciation = float(params.get("annual_appreciation_pct", 3.0)) / 100
    expenses_pct = float(params.get("annual_expenses_pct", 2.0)) / 100
    vacancy = float(params.get("vacancy_rate_pct", 5.0)) / 100
    closing_costs_pct = float(params.get("closing_costs_pct", 3.0)) / 100
    rent_increase = float(params.get("annual_rent_increase_pct", 2.0)) / 100

    if purchase_price <= 0 or monthly_rent <= 0 or years <= 0:
        raise ValueError("purchase_price_usd, monthly_rent_usd, and holding_period_years must be positive")

    # Initial outlay (negative cash flow)
    initial_cost = purchase_price * (1 + closing_costs_pct)

    yearly_cashflows: list[dict[str, Any]] = []
    cash_flows_for_irr: list[float] = [-initial_cost]

    current_rent = monthly_rent
    property_value = purchase_price

    total_rental_income = 0.0
    total_expenses = 0.0

    for year in range(1, years + 1):
        # Rental income (adjusted for vacancy)
        gross_rent = current_rent * 12
        effective_rent = gross_rent * (1 - vacancy)

        # Annual expenses
        annual_expenses = property_value * expenses_pct

        # Net operating income
        net_income = effective_rent - annual_expenses

        total_rental_income += effective_rent
        total_expenses += annual_expenses

        # Appreciation
        property_value *= (1 + appreciation)

        # In the final year, add sale proceeds (after selling costs)
        sale_proceeds = 0.0
        if year == years:
            sale_proceeds = property_value * (1 - closing_costs_pct)

        annual_cf = net_income + sale_proceeds
        cash_flows_for_irr.append(annual_cf)

        yearly_cashflows.append({
            "year": year,
            "gross_rent": round(gross_rent, 2),
            "effective_rent": round(effective_rent, 2),
            "expenses": round(annual_expenses, 2),
            "net_income": round(net_income, 2),
            "property_value": round(property_value, 2),
            "sale_proceeds": round(sale_proceeds, 2) if sale_proceeds else None,
            "total_cash_flow": round(annual_cf, 2),
        })

        # Escalate rent
        current_rent *= (1 + rent_increase)

    # Compute IRR via Newton-Raphson iteration
    irr = _compute_irr(cash_flows_for_irr)

    # Total return
    total_cash_in = sum(cf for cf in cash_flows_for_irr[1:])
    total_return = (total_cash_in - initial_cost) / initial_cost * 100

    # NPV at a conventional 8% discount rate
    discount_rate = 0.08
    npv = _compute_npv(discount_rate, cash_flows_for_irr)

    return {
        "initial_investment": round(initial_cost, 2),
        "final_property_value": round(property_value, 2),
        "total_rental_income": round(total_rental_income, 2),
        "total_expenses": round(total_expenses, 2),
        "total_return_pct": round(total_return, 2),
        "irr_pct": round(irr * 100, 2) if irr is not None else None,
        "npv_at_8pct": round(npv, 2),
        "holding_period_years": years,
        "yearly_cashflows": yearly_cashflows,
    }


# ── Opportunities ─────────────────────────────────────────────────────

async def get_opportunities(
    db: AsyncSession,
    operation_type: str = "sale",
    threshold: float = 0.8,
    limit: int = 50,
) -> dict[str, Any]:
    """Find listings priced below the barrio median by *threshold*.

    E.g. threshold=0.8 means 20% below median.
    """
    # Latest snapshot per barrio
    latest_sub = (
        select(
            BarrioSnapshot.barrio_id,
            func.max(BarrioSnapshot.snapshot_date).label("max_date"),
        )
        .where(BarrioSnapshot.operation_type == operation_type)
        .group_by(BarrioSnapshot.barrio_id)
        .subquery()
    )

    snap = (
        select(
            BarrioSnapshot.barrio_id,
            BarrioSnapshot.median_price_usd_m2,
        )
        .join(
            latest_sub,
            (BarrioSnapshot.barrio_id == latest_sub.c.barrio_id)
            & (BarrioSnapshot.snapshot_date == latest_sub.c.max_date),
        )
        .where(
            BarrioSnapshot.operation_type == operation_type,
            BarrioSnapshot.median_price_usd_m2.isnot(None),
            BarrioSnapshot.median_price_usd_m2 > 0,
        )
        .subquery()
    )

    # Compute listing price/m2
    listing_price_m2 = (
        cast(Listing.price_usd_blue, Float) / cast(Listing.surface_total_m2, Float)
    )

    stmt = (
        select(
            Listing.id,
            Listing.title,
            Listing.property_type,
            Listing.operation_type,
            Listing.price_usd_blue,
            Listing.surface_total_m2,
            listing_price_m2.label("price_usd_m2"),
            Listing.rooms,
            Listing.bedrooms,
            Listing.url,
            Barrio.name.label("barrio_name"),
            Barrio.slug.label("barrio_slug"),
            snap.c.median_price_usd_m2.label("median_price_usd_m2"),
        )
        .join(Barrio, Listing.barrio_id == Barrio.id)
        .join(snap, Listing.barrio_id == snap.c.barrio_id)
        .where(
            Listing.is_active.is_(True),
            Listing.operation_type == operation_type,
            Listing.price_usd_blue.isnot(None),
            Listing.price_usd_blue > 0,
            Listing.surface_total_m2.isnot(None),
            Listing.surface_total_m2 > 0,
            listing_price_m2 < snap.c.median_price_usd_m2 * threshold,
        )
        .order_by(
            (listing_price_m2 / snap.c.median_price_usd_m2).asc()
        )
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    items: list[dict[str, Any]] = []
    discount_sum = 0.0
    barrio_counts: dict[str, int] = {}

    for row in rows:
        price_m2 = float(row.price_usd_m2)
        median = float(row.median_price_usd_m2)
        discount_pct = round((1 - price_m2 / median) * 100, 1)
        discount_sum += discount_pct

        barrio_counts[row.barrio_name] = barrio_counts.get(row.barrio_name, 0) + 1

        items.append({
            "id": str(row.id),
            "title": row.title,
            "property_type": row.property_type,
            "operation_type": row.operation_type,
            "price_usd_blue": float(row.price_usd_blue) if row.price_usd_blue else None,
            "surface_total_m2": float(row.surface_total_m2) if row.surface_total_m2 else None,
            "price_usd_m2": round(price_m2, 2),
            "rooms": row.rooms,
            "bedrooms": row.bedrooms,
            "barrio_name": row.barrio_name,
            "barrio_slug": row.barrio_slug,
            "median_price_usd_m2": round(median, 2),
            "discount_pct": discount_pct,
            "url": row.url,
        })

    avg_discount = round(discount_sum / len(items), 1) if items else None
    top_barrio = max(barrio_counts, key=barrio_counts.get) if barrio_counts else None

    return {
        "items": items,
        "total": len(items),
        "avg_discount_pct": avg_discount,
        "top_barrio": top_barrio,
    }


# ── IRR / NPV helpers ────────────────────────────────────────────────

def _compute_npv(rate: float, cash_flows: list[float]) -> float:
    """Compute Net Present Value given a discount rate and cash flows."""
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))


def _compute_irr(
    cash_flows: list[float],
    max_iterations: int = 200,
    tolerance: float = 1e-7,
) -> float | None:
    """Compute Internal Rate of Return using Newton-Raphson iteration.

    Returns the IRR as a decimal (e.g. 0.12 for 12%), or ``None`` if
    convergence fails.
    """
    # Initial guess
    guess = 0.10

    for _ in range(max_iterations):
        npv = 0.0
        d_npv = 0.0  # derivative of NPV w.r.t. rate
        for t, cf in enumerate(cash_flows):
            denom = (1 + guess) ** t
            if denom == 0:
                return None
            npv += cf / denom
            if t > 0:
                d_npv -= t * cf / ((1 + guess) ** (t + 1))

        if abs(d_npv) < 1e-14:
            # Derivative too small — cannot continue
            return None

        new_guess = guess - npv / d_npv

        if abs(new_guess - guess) < tolerance:
            return new_guess

        guess = new_guess

    # Did not converge
    logger.warning("IRR computation did not converge after %d iterations", max_iterations)
    return None
