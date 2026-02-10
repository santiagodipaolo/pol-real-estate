"""Celery task -- compute daily barrio snapshots.

For each (barrio, operation_type) combination this task calculates aggregated
statistics from active listings and writes (or upserts) a row into the
``barrio_snapshots`` table.

Like the currency task, this module uses synchronous SQLAlchemy because Celery
workers operate in a synchronous context.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine, text, func, select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.barrio import Barrio
from app.models.barrio_snapshot import BarrioSnapshot
from app.models.currency_rate import CurrencyRate
from app.models.listing import Listing
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_latest_blue_rate(session: Session) -> float | None:
    """Return the most recent blue dollar sell rate, or ``None``."""
    result = session.execute(
        select(CurrencyRate.sell)
        .where(CurrencyRate.rate_type == "blue")
        .order_by(CurrencyRate.recorded_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row is not None else None


def _compute_snapshot_for_group(
    session: Session,
    barrio_id: int,
    operation_type: str,
    snapshot_date: date,
) -> dict | None:
    """Compute aggregated statistics for a single (barrio, operation_type)
    group using raw SQL for percentile functions (PostgreSQL-specific).

    Returns a dict suitable for inserting into ``barrio_snapshots``, or
    ``None`` if there are no matching active listings.
    """
    # Use raw SQL for percentile_cont which is PostgreSQL-specific
    stats_sql = text("""
        SELECT
            COUNT(*)                                                 AS listing_count,
            AVG(price_usd_blue / NULLIF(surface_covered_m2, 0))     AS avg_price_usd_m2,
            PERCENTILE_CONT(0.50) WITHIN GROUP (
                ORDER BY price_usd_blue / NULLIF(surface_covered_m2, 0)
            )                                                        AS median_price_usd_m2,
            PERCENTILE_CONT(0.25) WITHIN GROUP (
                ORDER BY price_usd_blue / NULLIF(surface_covered_m2, 0)
            )                                                        AS p25_price_usd_m2,
            PERCENTILE_CONT(0.75) WITHIN GROUP (
                ORDER BY price_usd_blue / NULLIF(surface_covered_m2, 0)
            )                                                        AS p75_price_usd_m2,
            AVG(days_on_market)                                      AS avg_days_on_market
        FROM listings
        WHERE barrio_id = :barrio_id
          AND operation_type = :operation_type
          AND is_active = true
          AND price_usd_blue IS NOT NULL
          AND surface_covered_m2 IS NOT NULL
          AND surface_covered_m2 > 0
    """)

    result = session.execute(
        stats_sql,
        {"barrio_id": barrio_id, "operation_type": operation_type},
    )
    row = result.one()

    if row.listing_count == 0:
        return None

    # New listings in the last 7 days
    seven_days_ago = snapshot_date - timedelta(days=7)
    new_count = session.execute(
        select(func.count(Listing.id)).where(
            and_(
                Listing.barrio_id == barrio_id,
                Listing.operation_type == operation_type,
                Listing.is_active.is_(True),
                func.date(Listing.first_seen_at) >= seven_days_ago,
            )
        )
    ).scalar_one()

    # Removed listings in the last 7 days (last_seen_at in the past 7 days
    # but no longer active)
    removed_count = session.execute(
        select(func.count(Listing.id)).where(
            and_(
                Listing.barrio_id == barrio_id,
                Listing.operation_type == operation_type,
                Listing.is_active.is_(False),
                func.date(Listing.last_seen_at) >= seven_days_ago,
            )
        )
    ).scalar_one()

    return {
        "barrio_id": barrio_id,
        "snapshot_date": snapshot_date,
        "operation_type": operation_type,
        "property_type": None,  # aggregated across all property types
        "listing_count": row.listing_count,
        "median_price_usd_m2": round(row.median_price_usd_m2, 2) if row.median_price_usd_m2 else None,
        "avg_price_usd_m2": round(row.avg_price_usd_m2, 2) if row.avg_price_usd_m2 else None,
        "p25_price_usd_m2": round(row.p25_price_usd_m2, 2) if row.p25_price_usd_m2 else None,
        "p75_price_usd_m2": round(row.p75_price_usd_m2, 2) if row.p75_price_usd_m2 else None,
        "avg_days_on_market": round(row.avg_days_on_market, 1) if row.avg_days_on_market else None,
        "new_listings_7d": new_count,
        "removed_listings_7d": removed_count,
    }


@celery_app.task(
    name="app.tasks.snapshot_tasks.compute_daily_snapshots",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def compute_daily_snapshots(self) -> dict:
    """Compute and store daily barrio snapshots for all (barrio, operation_type)
    combinations.

    Returns a summary with the total number of snapshots written.
    """
    engine = create_engine(settings.sync_database_url)
    today = date.today()
    written = 0

    try:
        with Session(engine) as session:
            # Get the latest blue rate to embed in each snapshot row
            blue_rate = _get_latest_blue_rate(session)

            # Fetch all barrio IDs
            barrio_ids = [
                row[0]
                for row in session.execute(select(Barrio.id)).all()
            ]

            # Determine the distinct operation types present in listings
            operation_types = [
                row[0]
                for row in session.execute(
                    select(Listing.operation_type).distinct()
                ).all()
            ]

            if not barrio_ids or not operation_types:
                logger.warning("No barrios or operation types found; skipping snapshot.")
                return {"written": 0, "snapshot_date": today.isoformat()}

            for barrio_id in barrio_ids:
                for op_type in operation_types:
                    snapshot_data = _compute_snapshot_for_group(
                        session, barrio_id, op_type, today
                    )
                    if snapshot_data is None:
                        continue

                    snapshot_data["usd_blue_rate"] = blue_rate

                    # Upsert: insert or update on conflict
                    stmt = pg_insert(BarrioSnapshot).values(**snapshot_data)
                    stmt = stmt.on_conflict_do_update(
                        constraint="uq_barrio_snapshot",
                        set_={
                            "listing_count": stmt.excluded.listing_count,
                            "median_price_usd_m2": stmt.excluded.median_price_usd_m2,
                            "avg_price_usd_m2": stmt.excluded.avg_price_usd_m2,
                            "p25_price_usd_m2": stmt.excluded.p25_price_usd_m2,
                            "p75_price_usd_m2": stmt.excluded.p75_price_usd_m2,
                            "avg_days_on_market": stmt.excluded.avg_days_on_market,
                            "new_listings_7d": stmt.excluded.new_listings_7d,
                            "removed_listings_7d": stmt.excluded.removed_listings_7d,
                            "usd_blue_rate": stmt.excluded.usd_blue_rate,
                        },
                    )
                    session.execute(stmt)
                    written += 1

            session.commit()
    except Exception as exc:
        logger.error("Snapshot computation failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        engine.dispose()

    logger.info("Wrote %d snapshots for %s", written, today.isoformat())
    return {"written": written, "snapshot_date": today.isoformat()}
