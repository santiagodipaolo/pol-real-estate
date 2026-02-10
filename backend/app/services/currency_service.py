"""Currency rate service — fetches live rates from DolarAPI / Bluelytics and
persists them to the database."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.currency_rate import CurrencyRate

logger = logging.getLogger(__name__)

# ── Mapping from DolarAPI's "casa" field to our rate_type ──────────────
_CASA_MAP: dict[str, str] = {
    "blue": "blue",
    "oficial": "official",
    "bolsa": "mep",
    "contadoconliqui": "ccl",
    "mayorista": "mayorista",
    "cripto": "cripto",
    "tarjeta": "tarjeta",
}


# ── External API calls ────────────────────────────────────────────────

async def fetch_current_rates() -> dict[str, Any]:
    """Fetch the latest dollar exchange rates from DolarAPI.

    Returns a dict keyed by rate_type (blue, official, mep, ccl, ...)
    with ``buy`` and ``sell`` prices in ARS.
    """
    url = f"{settings.DOLAR_API_BASE_URL}/dolares"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("DolarAPI returned HTTP %s: %s", exc.response.status_code, exc.response.text)
        raise
    except httpx.RequestError as exc:
        logger.error("DolarAPI request failed: %s", exc)
        raise

    rates: dict[str, Any] = {}
    for item in data:
        casa = item.get("casa", "").lower()
        rate_type = _CASA_MAP.get(casa)
        if rate_type is None:
            continue
        rates[rate_type] = {
            "buy": item.get("compra"),
            "sell": item.get("venta"),
            "source": "dolarapi",
        }
    return rates


async def fetch_bluelytics_history(
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[dict[str, Any]]:
    """Fetch historical blue / official dollar rates from Bluelytics.

    The Bluelytics ``/v2/evolution.json`` endpoint returns the full
    history.  We filter client-side by the requested date range.
    """
    url = f"{settings.BLUELYTICS_API_URL}/evolution.json"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data: list[dict[str, Any]] = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("Bluelytics returned HTTP %s: %s", exc.response.status_code, exc.response.text)
        raise
    except httpx.RequestError as exc:
        logger.error("Bluelytics request failed: %s", exc)
        raise

    results: list[dict[str, Any]] = []
    for entry in data:
        raw_date = entry.get("date")
        if raw_date is None:
            continue
        try:
            entry_date = datetime.fromisoformat(raw_date).date()
        except (ValueError, TypeError):
            continue

        if from_date and entry_date < from_date:
            continue
        if to_date and entry_date > to_date:
            continue

        results.append({
            "date": entry_date.isoformat(),
            "source": entry.get("source", "bluelytics"),
            "blue_buy": entry.get("blue", {}).get("value_buy"),
            "blue_sell": entry.get("blue", {}).get("value_sell"),
            "official_buy": entry.get("official", {}).get("value_buy"),
            "official_sell": entry.get("official", {}).get("value_sell"),
        })

    return results


# ── Database helpers ──────────────────────────────────────────────────

async def save_rates(db: AsyncSession, rates: dict[str, Any]) -> list[CurrencyRate]:
    """Persist a ``rates`` dict (as returned by :func:`fetch_current_rates`)
    to the ``currency_rates`` table.

    Returns the list of created :class:`CurrencyRate` instances.
    """
    records: list[CurrencyRate] = []
    now = datetime.utcnow()
    for rate_type, values in rates.items():
        record = CurrencyRate(
            rate_type=rate_type,
            buy=values.get("buy"),
            sell=values.get("sell"),
            source=values.get("source", "dolarapi"),
            recorded_at=now,
        )
        db.add(record)
        records.append(record)

    await db.commit()
    for r in records:
        await db.refresh(r)
    return records


async def get_latest_rates(db: AsyncSession) -> dict[str, Any]:
    """Return the most recent CurrencyRate row for each distinct rate_type,
    formatted as a dict matching CurrencyRatesAll schema."""
    from sqlalchemy import func

    subq = (
        select(
            CurrencyRate.rate_type,
            func.max(CurrencyRate.recorded_at).label("max_recorded"),
        )
        .group_by(CurrencyRate.rate_type)
        .subquery()
    )

    stmt = (
        select(CurrencyRate)
        .join(
            subq,
            (CurrencyRate.rate_type == subq.c.rate_type)
            & (CurrencyRate.recorded_at == subq.c.max_recorded),
        )
        .order_by(CurrencyRate.rate_type)
    )

    result = await db.execute(stmt)
    rates = list(result.scalars().all())

    output: dict[str, Any] = {"retrieved_at": datetime.utcnow()}
    for r in rates:
        output[r.rate_type] = {
            "rate_type": r.rate_type,
            "buy": r.buy,
            "sell": r.sell,
            "source": r.source,
            "recorded_at": r.recorded_at,
        }
    return output


async def get_rate_history(
    db: AsyncSession,
    rate_type: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, Any]:
    """Return historical CurrencyRate records formatted as CurrencyHistory."""
    from sqlalchemy import cast, Date

    stmt = (
        select(CurrencyRate)
        .where(CurrencyRate.rate_type == rate_type)
    )

    if from_date:
        stmt = stmt.where(cast(CurrencyRate.recorded_at, Date) >= from_date)
    if to_date:
        stmt = stmt.where(cast(CurrencyRate.recorded_at, Date) <= to_date)

    stmt = stmt.order_by(CurrencyRate.recorded_at)

    result = await db.execute(stmt)
    rates = list(result.scalars().all())

    return {
        "rate_type": rate_type,
        "points": [
            {
                "date": r.recorded_at.date() if r.recorded_at else None,
                "buy": r.buy,
                "sell": r.sell,
            }
            for r in rates
        ],
    }
