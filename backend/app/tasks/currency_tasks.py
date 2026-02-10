"""Celery task -- fetch live exchange rates from DolarAPI and persist them.

This module uses *synchronous* SQLAlchemy (``create_engine``) because Celery
workers run in a synchronous context.  The async ``httpx`` call is replaced by
the synchronous ``httpx.Client`` equivalent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.currency_rate import CurrencyRate
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Mapping from DolarAPI "casa" field to our rate_type
_CASA_MAP: dict[str, str] = {
    "blue": "blue",
    "oficial": "official",
    "bolsa": "mep",
    "contadoconliqui": "ccl",
    "mayorista": "mayorista",
    "cripto": "cripto",
    "tarjeta": "tarjeta",
}


def _fetch_rates_from_api() -> dict[str, dict]:
    """Call DolarAPI synchronously and return parsed rate data."""
    url = f"{settings.DOLAR_API_BASE_URL}/dolares"
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()

    rates: dict[str, dict] = {}
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


@celery_app.task(
    name="app.tasks.currency_tasks.fetch_and_save_rates",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def fetch_and_save_rates(self) -> dict:
    """Fetch the latest exchange rates from DolarAPI and insert them into the
    ``currency_rates`` table.

    Returns a summary dict with the number of rates saved.
    """
    try:
        rates = _fetch_rates_from_api()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.error("DolarAPI request failed: %s", exc)
        raise self.retry(exc=exc)

    if not rates:
        logger.warning("DolarAPI returned no usable rates")
        return {"saved": 0}

    engine = create_engine(settings.sync_database_url)
    now = datetime.now(timezone.utc)

    saved = 0
    with Session(engine) as session:
        for rate_type, values in rates.items():
            record = CurrencyRate(
                rate_type=rate_type,
                buy=values.get("buy"),
                sell=values.get("sell"),
                source=values.get("source", "dolarapi"),
                recorded_at=now,
            )
            session.add(record)
            saved += 1
        session.commit()

    engine.dispose()

    logger.info("Saved %d currency rates at %s", saved, now.isoformat())
    return {"saved": saved, "recorded_at": now.isoformat()}
