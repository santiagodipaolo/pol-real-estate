#!/usr/bin/env python3
"""
Fetch current and historical ARS/USD exchange rates and save to the database.

Sources:
  - DolarAPI  (https://dolarapi.com/v1/dolares)    -- current rates
  - Bluelytics (https://api.bluelytics.com.ar/v2)  -- historical evolution

Usage:
    python scripts/fetch_currency.py [--current] [--history] [--history-limit N]

Options:
    --current         Fetch current rates from DolarAPI (default: on).
    --history         Fetch historical rates from Bluelytics.
    --history-limit   Maximum number of historical records to import. Default: 365.
    --no-current      Skip fetching current rates.

When called without flags, only current rates are fetched.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup so we can import backend modules when running from project root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.currency_rate import CurrencyRate
from app.core.database import Base

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API URLs
# ---------------------------------------------------------------------------
DOLAR_API_URL = f"{settings.DOLAR_API_BASE_URL}/dolares"
BLUELYTICS_EVOLUTION_URL = f"{settings.BLUELYTICS_API_URL}/evolution.json"
BLUELYTICS_LATEST_URL = f"{settings.BLUELYTICS_API_URL}/latest"

# Mapping from DolarAPI "casa" field to our rate_type
DOLAR_API_TYPE_MAP = {
    "blue": "blue",
    "oficial": "official",
    "bolsa": "mep",
    "contadoconliqui": "ccl",
    "cripto": "crypto",
    "mayorista": "wholesale",
    "tarjeta": "tourist",
}


def _get_session():
    """Create a sync SQLAlchemy session."""
    db_url = settings.sync_database_url
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def fetch_current_rates() -> list[dict]:
    """
    Fetch current exchange rates from DolarAPI.

    Returns a list of dicts with keys: rate_type, buy, sell, source, recorded_at.
    """
    logger.info("Fetching current rates from DolarAPI: %s", DOLAR_API_URL)
    records = []

    try:
        resp = httpx.get(DOLAR_API_URL, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list):
            logger.error("Unexpected DolarAPI response format (expected list): %s", type(data))
            return records

        now = datetime.now(timezone.utc)

        for entry in data:
            casa = (entry.get("casa") or "").lower().strip()
            rate_type = DOLAR_API_TYPE_MAP.get(casa)
            if not rate_type:
                logger.debug("Skipping unknown DolarAPI casa: '%s'", casa)
                continue

            buy = entry.get("compra")
            sell = entry.get("venta")

            if buy is None and sell is None:
                continue

            # Parse the fechaActualizacion if available
            fecha_str = entry.get("fechaActualizacion")
            recorded_at = now
            if fecha_str:
                try:
                    recorded_at = datetime.fromisoformat(fecha_str)
                    if recorded_at.tzinfo is None:
                        recorded_at = recorded_at.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

            records.append({
                "rate_type": rate_type,
                "buy": float(buy) if buy is not None else None,
                "sell": float(sell) if sell is not None else None,
                "source": "dolarapi",
                "recorded_at": recorded_at,
            })

        logger.info("Parsed %d current rate entries from DolarAPI.", len(records))

    except httpx.HTTPStatusError as exc:
        logger.error("DolarAPI HTTP error: %s", exc)
    except httpx.RequestError as exc:
        logger.error("DolarAPI request error: %s", exc)
    except Exception as exc:
        logger.error("Unexpected error fetching from DolarAPI: %s", exc)

    # Fallback: try Bluelytics latest if DolarAPI failed
    if not records:
        logger.info("Falling back to Bluelytics latest endpoint...")
        records = _fetch_bluelytics_latest()

    return records


def _fetch_bluelytics_latest() -> list[dict]:
    """Fetch latest rates from Bluelytics as a fallback."""
    records = []
    try:
        resp = httpx.get(BLUELYTICS_LATEST_URL, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        now = datetime.now(timezone.utc)

        # Bluelytics returns: { "oficial": {"value_avg": ..., "value_sell": ..., "value_buy": ...}, "blue": {...}, ... }
        for key, rate_type in [("blue", "blue"), ("oficial", "official"), ("oficial_euro", "official_euro")]:
            entry = data.get(key)
            if not entry:
                continue
            buy = entry.get("value_buy")
            sell = entry.get("value_sell")
            if buy is None and sell is None:
                continue
            records.append({
                "rate_type": rate_type,
                "buy": float(buy) if buy is not None else None,
                "sell": float(sell) if sell is not None else None,
                "source": "bluelytics",
                "recorded_at": now,
            })

        logger.info("Parsed %d entries from Bluelytics latest.", len(records))
    except Exception as exc:
        logger.error("Error fetching Bluelytics latest: %s", exc)

    return records


def fetch_historical_rates(limit: int = 365) -> list[dict]:
    """
    Fetch historical blue dollar evolution from Bluelytics.

    Returns a list of dicts with keys: rate_type, buy, sell, source, recorded_at.
    """
    logger.info(
        "Fetching historical rates from Bluelytics: %s (limit=%d)",
        BLUELYTICS_EVOLUTION_URL,
        limit,
    )
    records = []

    try:
        # The evolution endpoint can return a large payload; increase timeout
        resp = httpx.get(
            BLUELYTICS_EVOLUTION_URL,
            timeout=60.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list):
            logger.error(
                "Unexpected Bluelytics evolution response format (expected list): %s",
                type(data),
            )
            return records

        count = 0
        for entry in data:
            if count >= limit:
                break

            source_name = (entry.get("source") or "").lower()
            rate_type = None
            if "blue" in source_name or source_name == "blue":
                rate_type = "blue"
            elif "oficial" in source_name or source_name == "oficial":
                rate_type = "official"
            else:
                rate_type = source_name or "blue"

            buy = entry.get("value_buy")
            sell = entry.get("value_sell")
            date_str = entry.get("date")

            if buy is None and sell is None:
                continue

            recorded_at = datetime.now(timezone.utc)
            if date_str:
                try:
                    recorded_at = datetime.fromisoformat(date_str)
                    if recorded_at.tzinfo is None:
                        recorded_at = recorded_at.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

            records.append({
                "rate_type": rate_type,
                "buy": float(buy) if buy is not None else None,
                "sell": float(sell) if sell is not None else None,
                "source": "bluelytics",
                "recorded_at": recorded_at,
            })
            count += 1

        logger.info("Parsed %d historical rate entries from Bluelytics.", len(records))

    except httpx.HTTPStatusError as exc:
        logger.error("Bluelytics HTTP error: %s", exc)
    except httpx.RequestError as exc:
        logger.error("Bluelytics request error: %s", exc)
    except Exception as exc:
        logger.error("Unexpected error fetching from Bluelytics: %s", exc)

    return records


def save_rates(records: list[dict]) -> int:
    """
    Save rate records to the currency_rates table.

    Skips duplicates based on (rate_type, source, recorded_at).
    Returns the number of new records inserted.
    """
    if not records:
        logger.info("No records to save.")
        return 0

    session, engine = _get_session()
    inserted = 0

    try:
        for rec in records:
            # Check for duplicates (exact match on type + source + timestamp)
            exists = session.execute(
                text(
                    "SELECT 1 FROM currency_rates "
                    "WHERE rate_type = :rate_type "
                    "  AND source = :source "
                    "  AND recorded_at = :recorded_at "
                    "LIMIT 1"
                ),
                {
                    "rate_type": rec["rate_type"],
                    "source": rec["source"],
                    "recorded_at": rec["recorded_at"],
                },
            ).fetchone()

            if exists:
                continue

            currency_rate = CurrencyRate(
                rate_type=rec["rate_type"],
                buy=rec["buy"],
                sell=rec["sell"],
                source=rec["source"],
                recorded_at=rec["recorded_at"],
            )
            session.add(currency_rate)
            inserted += 1

        session.commit()
        logger.info("Inserted %d new currency rate records.", inserted)

    except Exception:
        session.rollback()
        logger.exception("Error saving currency rates.")
        raise
    finally:
        session.close()
        engine.dispose()

    return inserted


def fetch_and_save_current() -> int:
    """Convenience: fetch current rates and save. Returns count inserted."""
    records = fetch_current_rates()
    return save_rates(records)


def fetch_and_save_history(limit: int = 365) -> int:
    """Convenience: fetch historical rates and save. Returns count inserted."""
    records = fetch_historical_rates(limit=limit)
    return save_rates(records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch ARS/USD exchange rates and save to the database."
    )
    parser.add_argument(
        "--current",
        action="store_true",
        default=False,
        help="Fetch current rates from DolarAPI.",
    )
    parser.add_argument(
        "--no-current",
        action="store_true",
        default=False,
        help="Skip fetching current rates.",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        default=False,
        help="Fetch historical rates from Bluelytics.",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=365,
        help="Maximum number of historical records to import. Default: 365.",
    )
    args = parser.parse_args()

    # Default behavior: if neither --current nor --history is specified, fetch current
    fetch_current = True
    fetch_history = args.history

    if args.no_current:
        fetch_current = False

    if not args.current and not args.history and not args.no_current:
        fetch_current = True

    total_inserted = 0

    if fetch_current:
        logger.info("--- Fetching current rates ---")
        count = fetch_and_save_current()
        total_inserted += count

    if fetch_history:
        logger.info("--- Fetching historical rates ---")
        count = fetch_and_save_history(limit=args.history_limit)
        total_inserted += count

    logger.info("Done. Total new records saved: %d", total_inserted)


if __name__ == "__main__":
    main()
