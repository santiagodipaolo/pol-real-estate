"""CLI script to run the Zonaprop scraper.

Usage:
    cd backend
    python -m scripts.scrape                    # Default: 5 pages sale + 5 pages rent
    python -m scripts.scrape --operation sale    # Only sale
    python -m scripts.scrape --operation rent    # Only rent
    python -m scripts.scrape --pages 10          # 10 pages per operation
    python -m scripts.scrape --headful           # Show browser (for debugging)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

# Ensure backend dir is in path
sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scrape")


async def run(operation: str | None, max_pages: int, headless: bool) -> None:
    from app.scrapers.zonaprop import ZonapropScraper
    from app.scrapers.pipeline import save_listings

    scraper = ZonapropScraper(headless=headless)

    operations = [operation] if operation else ["sale", "rent"]
    total_results = {"created": 0, "updated": 0, "skipped": 0}

    try:
        for op in operations:
            logger.info("=" * 60)
            logger.info("Scraping %s listings (max %d pages)...", op, max_pages)
            logger.info("=" * 60)

            listings = await scraper.scrape_listings(operation=op, max_pages=max_pages)
            logger.info("Scraped %d %s listings from Zonaprop", len(listings), op)

            if listings:
                result = save_listings(listings)
                for key in total_results:
                    total_results[key] += result[key]
                logger.info("Saved: %s", result)
    finally:
        await scraper.close()

    logger.info("=" * 60)
    logger.info("TOTAL: %s", total_results)
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Zonaprop listings")
    parser.add_argument(
        "--operation",
        choices=["sale", "rent"],
        default=None,
        help="Operation type (default: both)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="Max pages per operation (default: 5, ~20 listings/page)",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Show browser window (for debugging)",
    )
    args = parser.parse_args()

    asyncio.run(run(args.operation, args.pages, headless=not args.headful))


if __name__ == "__main__":
    main()
