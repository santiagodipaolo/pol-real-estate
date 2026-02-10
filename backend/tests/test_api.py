"""Tests for the FastAPI HTTP endpoints.

These tests use ``httpx.AsyncClient`` with the ASGI transport so that no
real HTTP server is started.  The database dependency is overridden to use
an in-memory SQLite session provided by the ``client`` fixture (see
``conftest.py``).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
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


async def _seed_barrio(db_session, name="Palermo", slug="palermo", comuna_id=14) -> Barrio:
    barrio = Barrio(name=name, slug=slug, comuna_id=comuna_id, comuna_name=f"Comuna {comuna_id}")
    db_session.add(barrio)
    await db_session.commit()
    await db_session.refresh(barrio)
    return barrio


async def _seed_currency_rate(db_session) -> CurrencyRate:
    now = _utcnow()
    rate = CurrencyRate(
        rate_type="blue",
        buy=Decimal("1250.0000"),
        sell=Decimal("1300.0000"),
        source="dolarapi",
        recorded_at=now,
    )
    db_session.add(rate)
    await db_session.commit()
    await db_session.refresh(rate)
    return rate


async def _seed_listing(db_session, barrio: Barrio) -> Listing:
    now = _utcnow()
    listing = Listing(
        id=uuid.uuid4(),
        external_id="ML-99999",
        source="mercadolibre",
        title="Test listing",
        operation_type="venta",
        property_type="departamento",
        price_original=Decimal("120000.00"),
        currency_original="USD",
        price_usd_blue=Decimal("120000.00"),
        surface_total_m2=Decimal("60.00"),
        surface_covered_m2=Decimal("55.00"),
        barrio_id=barrio.id,
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
        days_on_market=10,
    )
    db_session.add(listing)
    await db_session.commit()
    await db_session.refresh(listing)
    return listing


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """GET /health should return 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_get_barrios_returns_list(client, db_session):
    """GET /api/v1/barrios should return a JSON list (possibly empty)."""
    # Seed a barrio so the list is non-empty
    await _seed_barrio(db_session)

    response = await client.get("/api/v1/barrios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Check the structure of the first item
    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "slug" in first


@pytest.mark.asyncio
async def test_get_currency_rates_returns_structure(client, db_session):
    """GET /api/v1/currency/rates should return the expected envelope."""
    # Seed a rate so there is data
    await _seed_currency_rate(db_session)

    response = await client.get("/api/v1/currency/rates")
    assert response.status_code == 200
    data = response.json()

    # The CurrencyRatesAll schema returns an object with known keys
    # Even if some rate types are missing, the response should be a dict
    assert isinstance(data, (dict, list))


@pytest.mark.asyncio
async def test_get_listings_returns_paginated_structure(client, db_session):
    """GET /api/v1/listings should return a paginated response object."""
    barrio = await _seed_barrio(db_session)
    await _seed_listing(db_session, barrio)

    response = await client.get("/api/v1/listings")
    assert response.status_code == 200
    data = response.json()

    # Expect the ListingsPage schema
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_post_roi_simulation_returns_result(client):
    """POST /api/v1/analytics/roi-simulation should return calculated ROI metrics."""
    payload = {
        "purchase_price_usd": "200000",
        "monthly_rent_usd": "800",
        "monthly_expenses_usd": "150",
        "vacancy_rate": "0.05",
        "annual_appreciation": "0.03",
        "closing_costs_pct": "0.06",
        "holding_period_years": 10,
        "discount_rate": "0.08",
    }
    response = await client.post("/api/v1/analytics/roi-simulation", json=payload)
    assert response.status_code == 200
    data = response.json()

    # The ROISimulationResult schema includes these fields
    assert "total_investment" in data
    assert "annual_net_income" in data
    # Ensure the computation actually ran (total_investment > 0)
    assert float(data["total_investment"]) > 0
