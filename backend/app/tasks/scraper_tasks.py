"""Celery task — scrape Zonaprop listings periodically.

Runs synchronously in the Celery worker by delegating to the async scraper
via ``asyncio.run()``.
"""

from __future__ import annotations

import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_scrape(operation: str, max_pages: int) -> dict:
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


@celery_app.task(
    name="app.tasks.scraper_tasks.scrape_zonaprop",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def scrape_zonaprop(self, operation: str = "sale", max_pages: int = 5) -> dict:
    """Scrape Zonaprop listings and save to database.

    Args:
        operation: "sale" or "rent"
        max_pages: Number of search result pages to scrape.

    Returns:
        Summary dict with created/updated/skipped counts.
    """
    try:
        result = _run_scrape(operation, max_pages)
        logger.info("Zonaprop %s scrape done: %s", operation, result)
        return result
    except Exception as exc:
        logger.error("Zonaprop %s scrape failed: %s", operation, exc)
        raise self.retry(exc=exc)
