"""Tests for SQLAlchemy ORM model creation.

Each test inserts a model instance via the async test session and verifies
that the row is persisted with the expected column values.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.barrio import Barrio
from app.models.barrio_snapshot import BarrioSnapshot
from app.models.currency_rate import CurrencyRate
from app.models.listing import Listing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_barrio_creation(db_session):
    """A Barrio row can be created and read back."""
    barrio = Barrio(
        name="Palermo",
        slug="palermo",
        comuna_id=14,
        comuna_name="Comuna 14",
        area_km2=Decimal("15.8500"),
        centroid_lat=Decimal("-34.5800000"),
        centroid_lon=Decimal("-58.4300000"),
    )
    db_session.add(barrio)
    await db_session.commit()
    await db_session.refresh(barrio)

    assert barrio.id is not None
    assert barrio.name == "Palermo"
    assert barrio.slug == "palermo"
    assert barrio.comuna_id == 14
    assert barrio.comuna_name == "Comuna 14"
    assert barrio.area_km2 == Decimal("15.8500")

    # Verify via a fresh SELECT
    result = await db_session.execute(
        select(Barrio).where(Barrio.slug == "palermo")
    )
    fetched = result.scalar_one()
    assert fetched.id == barrio.id
    assert fetched.name == "Palermo"


@pytest.mark.asyncio
async def test_listing_creation(db_session):
    """A Listing row can be created with a foreign key to Barrio."""
    # Create the parent barrio first
    barrio = Barrio(name="Recoleta", slug="recoleta", comuna_id=2, comuna_name="Comuna 2")
    db_session.add(barrio)
    await db_session.commit()
    await db_session.refresh(barrio)

    now = _utcnow()
    listing_id = uuid.uuid4()
    listing = Listing(
        id=listing_id,
        external_id="ML-12345",
        source="mercadolibre",
        url="https://example.com/listing/12345",
        title="Departamento 3 ambientes en Recoleta",
        operation_type="venta",
        property_type="departamento",
        price_original=Decimal("150000.00"),
        currency_original="USD",
        price_usd_blue=Decimal("150000.00"),
        price_ars=Decimal("195000000.00"),
        surface_total_m2=Decimal("85.00"),
        surface_covered_m2=Decimal("75.00"),
        rooms=3,
        bedrooms=2,
        bathrooms=1,
        barrio_id=barrio.id,
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
        days_on_market=15,
    )
    db_session.add(listing)
    await db_session.commit()
    await db_session.refresh(listing)

    assert listing.id == listing_id
    assert listing.external_id == "ML-12345"
    assert listing.source == "mercadolibre"
    assert listing.operation_type == "venta"
    assert listing.property_type == "departamento"
    assert listing.price_usd_blue == Decimal("150000.00")
    assert listing.barrio_id == barrio.id
    assert listing.is_active is True
    assert listing.days_on_market == 15

    # Verify via SELECT
    result = await db_session.execute(
        select(Listing).where(Listing.id == listing_id)
    )
    fetched = result.scalar_one()
    assert fetched.title == "Departamento 3 ambientes en Recoleta"
    assert fetched.barrio_id == barrio.id


@pytest.mark.asyncio
async def test_currency_rate_creation(db_session):
    """A CurrencyRate row stores buy/sell values and metadata."""
    now = _utcnow()
    rate = CurrencyRate(
        rate_type="blue",
        buy=Decimal("1250.5000"),
        sell=Decimal("1300.0000"),
        source="dolarapi",
        recorded_at=now,
    )
    db_session.add(rate)
    await db_session.commit()
    await db_session.refresh(rate)

    assert rate.id is not None
    assert rate.rate_type == "blue"
    assert rate.buy == Decimal("1250.5000")
    assert rate.sell == Decimal("1300.0000")
    assert rate.source == "dolarapi"

    # Verify via SELECT
    result = await db_session.execute(
        select(CurrencyRate).where(CurrencyRate.rate_type == "blue")
    )
    fetched = result.scalar_one()
    assert fetched.id == rate.id
    assert fetched.sell == Decimal("1300.0000")


@pytest.mark.asyncio
async def test_barrio_snapshot_creation(db_session):
    """A BarrioSnapshot row stores aggregated stats for a barrio on a given date."""
    barrio = Barrio(name="Belgrano", slug="belgrano", comuna_id=13, comuna_name="Comuna 13")
    db_session.add(barrio)
    await db_session.commit()
    await db_session.refresh(barrio)

    today = date.today()
    snapshot = BarrioSnapshot(
        barrio_id=barrio.id,
        snapshot_date=today,
        operation_type="venta",
        property_type=None,
        listing_count=120,
        median_price_usd_m2=Decimal("2800.50"),
        avg_price_usd_m2=Decimal("3050.75"),
        p25_price_usd_m2=Decimal("2200.00"),
        p75_price_usd_m2=Decimal("3500.00"),
        avg_days_on_market=Decimal("45.3"),
        new_listings_7d=18,
        removed_listings_7d=5,
        rental_yield_estimate=Decimal("0.0420"),
        usd_blue_rate=Decimal("1300.0000"),
    )
    db_session.add(snapshot)
    await db_session.commit()
    await db_session.refresh(snapshot)

    assert snapshot.id is not None
    assert snapshot.barrio_id == barrio.id
    assert snapshot.snapshot_date == today
    assert snapshot.operation_type == "venta"
    assert snapshot.listing_count == 120
    assert snapshot.median_price_usd_m2 == Decimal("2800.50")
    assert snapshot.avg_price_usd_m2 == Decimal("3050.75")
    assert snapshot.p25_price_usd_m2 == Decimal("2200.00")
    assert snapshot.p75_price_usd_m2 == Decimal("3500.00")
    assert snapshot.avg_days_on_market == Decimal("45.3")
    assert snapshot.new_listings_7d == 18
    assert snapshot.removed_listings_7d == 5
    assert snapshot.usd_blue_rate == Decimal("1300.0000")

    # Verify via SELECT
    result = await db_session.execute(
        select(BarrioSnapshot).where(BarrioSnapshot.barrio_id == barrio.id)
    )
    fetched = result.scalar_one()
    assert fetched.listing_count == 120
    assert fetched.rental_yield_estimate == Decimal("0.0420")
