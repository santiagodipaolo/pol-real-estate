"""Admin endpoints — scraping, retraining, and pipeline management.

Protected by ADMIN_API_KEY. Designed to be called by Railway Cron Jobs
or manually for on-demand runs.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy import create_engine, text

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory status tracker (persists within the running process)
_run_status: dict[str, dict] = {}


def _verify_admin_key(x_admin_key: str = Header(...)) -> None:
    """Verify the admin API key from request header."""
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY not configured")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


def _update_status(task: str, **kwargs) -> None:
    _run_status[task] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }


def _run_scrape_sync(operation: str, max_pages: int) -> dict:
    """Run the async scraper in a sync context."""
    from app.scrapers.zonaprop import ZonapropScraper
    from app.scrapers.pipeline import save_listings

    async def _scrape():
        scraper = ZonapropScraper(headless=True)
        try:
            listings = await scraper.scrape_listings(
                operation=operation,
                max_pages=max_pages,
            )
            if listings:
                return save_listings(listings)
            return {"created": 0, "updated": 0, "skipped": 0}
        finally:
            await scraper.close()

    return asyncio.run(_scrape())


def _run_retrain_sync(operation: str) -> dict:
    """Train the valuation model from current DB data."""
    from app.valuation.model import ValuationModel

    engine = create_engine(settings.sync_database_url)
    query = text("""
        SELECT
            l.id, l.external_id, l.operation_type, l.property_type,
            l.price_usd_blue, l.price_ars, l.expenses_ars,
            l.surface_total_m2, l.surface_covered_m2,
            l.rooms, l.bedrooms, l.bathrooms, l.garages, l.age_years,
            l.barrio_id, l.latitude, l.longitude, l.days_on_market,
            b.name as barrio_name
        FROM listings l
        LEFT JOIN barrios b ON l.barrio_id = b.id
        WHERE l.operation_type = :operation
          AND l.is_active = true
          AND l.price_usd_blue > 0
          AND l.surface_total_m2 > 0
    """)

    df = pd.read_sql(query, engine, params={"operation": operation})
    engine.dispose()

    if len(df) < 20:
        return {"status": "skipped", "reason": f"Not enough data ({len(df)} listings, need 20+)"}

    model = ValuationModel()
    metrics = model.train(df)
    model_name = f"valuation_{operation}_v1"
    model.save(model_name)

    return {
        "status": "trained",
        "model_name": model_name,
        "samples": metrics["samples"],
        "mae_pct": round(metrics["mae_pct"], 1),
        "mae_cv": round(metrics["mae_cv"], 0),
    }


def _run_currency_sync() -> dict:
    """Fetch and save currency rates."""
    import httpx
    from sqlalchemy.orm import Session
    from app.models.currency_rate import CurrencyRate

    engine = create_engine(settings.sync_database_url)
    now = datetime.now(timezone.utc)
    saved = 0

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{settings.DOLAR_API_BASE_URL}/dolares")
            resp.raise_for_status()
            rates = resp.json()

        with Session(engine) as session:
            for rate_data in rates:
                rate = CurrencyRate(
                    rate_type=rate_data.get("casa", "unknown"),
                    buy=rate_data.get("compra"),
                    sell=rate_data.get("venta"),
                    source="dolarapi",
                    recorded_at=now,
                )
                session.add(rate)
                saved += 1
            session.commit()
    finally:
        engine.dispose()

    return {"saved": saved, "recorded_at": now.isoformat()}


def _background_pipeline(
    operations: list[str],
    max_pages: int,
    retrain: bool,
    fetch_rates: bool,
) -> None:
    """Run the full pipeline in background."""
    _update_status("pipeline", status="running", operations=operations)

    try:
        # 1. Fetch currency rates
        if fetch_rates:
            logger.info("Pipeline: fetching currency rates...")
            rates_result = _run_currency_sync()
            _update_status("currency", status="ok", **rates_result)
            logger.info("Pipeline: currency rates done: %s", rates_result)

        # 2. Scrape
        scrape_results = {}
        for op in operations:
            logger.info("Pipeline: scraping %s (%d pages)...", op, max_pages)
            result = _run_scrape_sync(op, max_pages)
            scrape_results[op] = result
            _update_status(f"scrape_{op}", status="ok", **result)
            logger.info("Pipeline: %s scrape done: %s", op, result)

        # 3. Retrain
        retrain_results = {}
        if retrain:
            for op in operations:
                logger.info("Pipeline: retraining %s model...", op)
                result = _run_retrain_sync(op)
                retrain_results[op] = result
                _update_status(f"retrain_{op}", status="ok", **result)
                logger.info("Pipeline: %s retrain done: %s", op, result)

            # Reload models in the valuation API (reset singleton)
            try:
                import app.api.v1.valuation as val_mod
                val_mod._model = None
                logger.info("Pipeline: valuation model cache cleared")
            except Exception:
                logger.warning("Pipeline: could not clear valuation model cache")

        _update_status("pipeline", status="completed",
                       scrape=scrape_results, retrain=retrain_results)
        logger.info("Pipeline completed successfully")

    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        _update_status("pipeline", status="failed", error=str(exc))


# --- Endpoints ---

@router.post("/scrape")
async def scrape(
    background_tasks: BackgroundTasks,
    operation: str = "sale",
    max_pages: int = 10,
    _: None = Depends(_verify_admin_key),
):
    """Trigger a scraping run. Runs in background."""
    if operation not in ("sale", "rent"):
        raise HTTPException(400, "operation must be 'sale' or 'rent'")
    if max_pages < 1 or max_pages > 100:
        raise HTTPException(400, "max_pages must be 1-100")

    _update_status(f"scrape_{operation}", status="running")
    background_tasks.add_task(_run_scrape_bg, operation, max_pages)
    return {"status": "started", "operation": operation, "max_pages": max_pages}


async def _run_scrape_bg(operation: str, max_pages: int):
    try:
        result = _run_scrape_sync(operation, max_pages)
        _update_status(f"scrape_{operation}", status="ok", **result)
        logger.info("Scrape %s done: %s", operation, result)
    except Exception as exc:
        _update_status(f"scrape_{operation}", status="failed", error=str(exc))
        logger.exception("Scrape %s failed", operation)


@router.post("/retrain")
async def retrain(
    background_tasks: BackgroundTasks,
    operation: str = "sale",
    _: None = Depends(_verify_admin_key),
):
    """Retrain the valuation model. Runs in background."""
    if operation not in ("sale", "rent"):
        raise HTTPException(400, "operation must be 'sale' or 'rent'")

    _update_status(f"retrain_{operation}", status="running")
    background_tasks.add_task(_run_retrain_bg, operation)
    return {"status": "started", "operation": operation}


async def _run_retrain_bg(operation: str):
    try:
        result = _run_retrain_sync(operation)
        _update_status(f"retrain_{operation}", status="ok", **result)
        logger.info("Retrain %s done: %s", operation, result)
    except Exception as exc:
        _update_status(f"retrain_{operation}", status="failed", error=str(exc))
        logger.exception("Retrain %s failed", operation)


@router.post("/pipeline")
async def pipeline(
    background_tasks: BackgroundTasks,
    max_pages: int = 10,
    retrain: bool = True,
    fetch_rates: bool = True,
    sale: bool = True,
    rent: bool = True,
    _: None = Depends(_verify_admin_key),
):
    """Run the full pipeline: fetch rates -> scrape -> retrain. Runs in background."""
    operations = []
    if sale:
        operations.append("sale")
    if rent:
        operations.append("rent")
    if not operations:
        raise HTTPException(400, "At least one operation (sale/rent) must be enabled")

    background_tasks.add_task(
        _background_pipeline, operations, max_pages, retrain, fetch_rates
    )
    return {
        "status": "started",
        "operations": operations,
        "max_pages": max_pages,
        "retrain": retrain,
        "fetch_rates": fetch_rates,
    }


@router.get("/status")
async def status(_: None = Depends(_verify_admin_key)):
    """Get the status of the last admin runs."""
    return _run_status
