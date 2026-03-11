"""Zonaprop scraper using Playwright.

Zonaprop is a Next.js application. The best extraction strategy is to
intercept the __NEXT_DATA__ JSON embedded in each page, which contains
structured listing data.  If that fails, we fall back to DOM extraction.
"""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any

from playwright.async_api import Browser, Page, Playwright, async_playwright

from app.scrapers.base import BaseScraper, RawListing

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------------
_BASE_URL = "https://www.zonaprop.com.ar"

_OPERATION_SLUGS = {
    "sale": "venta",
    "rent": "alquiler",
}

# Map Zonaprop property types to our standard types
_PROPERTY_TYPE_MAP = {
    "Departamento": "Departamento",
    "Departamentos": "Departamento",
    "Casa": "Casa",
    "Casas": "Casa",
    "PH": "PH",
    "PHs": "PH",
    "Local comercial": "Local",
    "Oficina": "Oficina",
    "Terreno": "Terreno",
    "Cochera": "Cochera",
}

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]


def _build_search_url(
    operation: str,
    property_types: list[str] | None = None,
    page: int = 1,
) -> str:
    """Build a Zonaprop search URL for Capital Federal.

    Examples:
        /departamentos-venta-capital-federal.html
        /departamentos-venta-capital-federal-pagina-2.html
        /departamentos-casas-ph-venta-capital-federal.html
    """
    op_slug = _OPERATION_SLUGS.get(operation, "venta")

    if property_types:
        type_slug = "-".join(t.lower() + "s" for t in property_types)
    else:
        type_slug = "departamentos-casas-ph"

    page_suffix = f"-pagina-{page}" if page > 1 else ""

    return f"{_BASE_URL}/{type_slug}-{op_slug}-capital-federal{page_suffix}.html"


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _extract_listing_from_posting(posting: dict, operation: str) -> RawListing | None:
    """Extract a RawListing from a Zonaprop posting object (from __NEXT_DATA__ or API)."""
    try:
        posting_id = str(posting.get("postingId", posting.get("id", "")))
        if not posting_id:
            return None

        # Price
        price_data = posting.get("priceOperationTypes", [{}])
        price_info = price_data[0] if price_data else {}
        prices = price_info.get("prices", [{}])
        price_obj = prices[0] if prices else {}
        amount = _safe_float(price_obj.get("amount"))
        currency = price_obj.get("currency", "USD")

        # Location
        geo = posting.get("postingLocation", {}).get("location", {})
        lat = _safe_float(geo.get("lat"))
        lng = _safe_float(geo.get("lng"))
        address = posting.get("postingLocation", {}).get("address", {}).get("name", "")
        barrio = posting.get("postingLocation", {}).get("location", {}).get("label", "")
        # Try to get barrio from the location hierarchy
        location_label = posting.get("postingLocation", {}).get("location", {})
        if not barrio:
            barrio = location_label.get("name", "")

        # Features
        main_features = posting.get("mainFeatures", {})
        surface_total = _safe_float(main_features.get("CFT100", main_features.get("surface")))
        surface_covered = _safe_float(main_features.get("CFT101", main_features.get("coveredSurface")))
        rooms = _safe_int(main_features.get("CFT2", main_features.get("rooms")))
        bedrooms = _safe_int(main_features.get("CFT3", main_features.get("bedrooms")))
        bathrooms = _safe_int(main_features.get("CFT4", main_features.get("bathrooms")))
        garages = _safe_int(main_features.get("CFT7", main_features.get("parkingLots")))

        # Expenses
        expenses_str = posting.get("expenses", {}).get("amount", None)
        expenses = _safe_float(expenses_str)

        # Property type
        raw_type = posting.get("realEstateType", {}).get("name", "Departamento")
        prop_type = _PROPERTY_TYPE_MAP.get(raw_type, raw_type)

        # URL
        url_path = posting.get("url", "")
        url = f"{_BASE_URL}{url_path}" if url_path and not url_path.startswith("http") else url_path

        title = posting.get("title", "")
        description = posting.get("description", "")

        # Age
        age = _safe_int(main_features.get("CFT6", main_features.get("antiqupiedad")))

        return RawListing(
            external_id=posting_id,
            source="zonaprop",
            url=url,
            title=title,
            operation_type=operation,
            property_type=prop_type,
            price=amount,
            currency=currency,
            expenses_ars=expenses,
            surface_total_m2=surface_total,
            surface_covered_m2=surface_covered,
            rooms=rooms,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            garages=garages,
            age_years=age,
            latitude=lat,
            longitude=lng,
            address=address,
            barrio_name=barrio,
            description=description,
        )
    except Exception:
        logger.exception("Failed to extract listing from posting %s", posting.get("postingId"))
        return None


class ZonapropScraper(BaseScraper):
    """Scraper for zonaprop.com.ar using Playwright."""

    source_name = "zonaprop"

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def _ensure_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
        return self._browser

    async def _new_page(self) -> Page:
        browser = await self._ensure_browser()
        context = await browser.new_context(
            user_agent=random.choice(_USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
        )
        page = await context.new_page()

        # Block images and fonts to speed things up
        await page.route(
            re.compile(r"\.(png|jpg|jpeg|gif|webp|svg|woff|woff2|ttf)$"),
            lambda route: route.abort(),
        )

        return page

    async def _extract_next_data(self, page: Page) -> dict | None:
        """Extract __NEXT_DATA__ JSON from the page."""
        try:
            el = await page.query_selector("script#__NEXT_DATA__")
            if el:
                text = await el.inner_text()
                return json.loads(text)
        except Exception:
            logger.debug("No __NEXT_DATA__ found, falling back to DOM extraction")
        return None

    async def _extract_from_next_data(
        self, next_data: dict, operation: str
    ) -> list[RawListing]:
        """Parse listings from __NEXT_DATA__ JSON."""
        listings: list[RawListing] = []
        try:
            # Navigate through Next.js data structure
            page_props = next_data.get("props", {}).get("pageProps", {})

            # Try different possible keys for listings
            postings = (
                page_props.get("listPostings", [])
                or page_props.get("postings", [])
                or page_props.get("listingsProps", {}).get("listPostings", [])
            )

            for posting in postings:
                raw = _extract_listing_from_posting(posting.get("posting", posting), operation)
                if raw:
                    listings.append(raw)

        except Exception:
            logger.exception("Failed to parse __NEXT_DATA__")

        return listings

    async def _extract_from_dom(self, page: Page, operation: str) -> list[RawListing]:
        """Extract listings directly from the DOM using data-qa selectors."""
        listings: list[RawListing] = []

        cards = await page.query_selector_all('[data-qa="posting PROPERTY"]')
        if not cards:
            cards = await page.query_selector_all(".postingCard")

        for card in cards:
            try:
                # Extract posting ID from the first link's href
                link_el = await card.query_selector("a[href]")
                href = await link_el.get_attribute("href") if link_el else ""
                if not href:
                    continue

                # ID is the last number in the URL: ...-58427158.html
                id_match = re.search(r"-(\d{6,})\.html", href)
                posting_id = id_match.group(1) if id_match else ""
                if not posting_id:
                    posting_id = await card.get_attribute("data-id") or ""
                if not posting_id:
                    continue

                # Price — from data-qa="POSTING_CARD_PRICE"
                price_el = await card.query_selector('[data-qa="POSTING_CARD_PRICE"]')
                price_text = (await price_el.inner_text()).strip() if price_el else ""

                amount = None
                currency = "USD"
                if price_text:
                    if "USD" in price_text or "U$S" in price_text:
                        currency = "USD"
                    elif "$" in price_text:
                        currency = "ARS"
                    # Remove dots (thousand separators) and parse
                    clean = price_text.replace(".", "").replace(",", ".")
                    numbers = re.findall(r"[\d]+(?:\.[\d]+)?", clean)
                    if numbers:
                        amount = _safe_float(numbers[0])

                # Expenses
                expenses = None
                expenses_el = await card.query_selector('[data-qa="expensas"]')
                if expenses_el:
                    exp_text = (await expenses_el.inner_text()).strip()
                    exp_nums = re.findall(r"[\d.]+", exp_text.replace(".", ""))
                    if exp_nums:
                        expenses = _safe_float(exp_nums[0])

                # Features — spans inside data-qa="POSTING_CARD_FEATURES"
                features_el = await card.query_selector_all(
                    '[data-qa="POSTING_CARD_FEATURES"] span'
                )
                surface_total = None
                surface_covered = None
                rooms_val = None
                bedrooms_val = None
                bathrooms_val = None
                garages_val = None

                for feat in features_el:
                    text = (await feat.inner_text()).strip().lower()
                    nums = re.findall(r"[\d]+(?:[.,][\d]+)?", text)
                    num = _safe_float(nums[0].replace(",", ".")) if nums else None

                    if "m² tot" in text and num:
                        surface_total = num
                    elif "m² cub" in text and num:
                        surface_covered = num
                    elif "m²" in text and num and not surface_total:
                        surface_total = num
                    elif "amb" in text and num:
                        rooms_val = _safe_int(num)
                    elif ("dorm" in text or "hab" in text) and num:
                        bedrooms_val = _safe_int(num)
                    elif "baño" in text and num:
                        bathrooms_val = _safe_int(num)
                    elif ("coch" in text or "garage" in text) and num:
                        garages_val = _safe_int(num)

                # Location — data-qa="POSTING_CARD_LOCATION"
                location_el = await card.query_selector('[data-qa="POSTING_CARD_LOCATION"]')
                location_text = (await location_el.inner_text()).strip() if location_el else ""
                barrio = location_text.split(",")[0].strip() if location_text else None

                # Description/Title
                desc_el = await card.query_selector('[data-qa="POSTING_CARD_DESCRIPTION"]')
                title = (await desc_el.inner_text()).strip() if desc_el else ""

                # URL
                url = f"{_BASE_URL}{href}" if not href.startswith("http") else href

                # Property type from URL
                prop_type = "Departamento"
                href_lower = href.lower()
                if "casa-en" in href_lower or "/casas" in href_lower:
                    prop_type = "Casa"
                elif "ph-en" in href_lower or "/ph" in href_lower:
                    prop_type = "PH"
                elif "local" in href_lower:
                    prop_type = "Local"
                elif "oficina" in href_lower:
                    prop_type = "Oficina"
                elif "terreno" in href_lower:
                    prop_type = "Terreno"

                listings.append(RawListing(
                    external_id=posting_id,
                    source="zonaprop",
                    url=url,
                    title=title,
                    operation_type=operation,
                    property_type=prop_type,
                    price=amount,
                    currency=currency,
                    expenses_ars=expenses,
                    surface_total_m2=surface_total,
                    surface_covered_m2=surface_covered,
                    rooms=rooms_val,
                    bedrooms=bedrooms_val,
                    bathrooms=bathrooms_val,
                    garages=garages_val,
                    barrio_name=barrio,
                ))
            except Exception:
                logger.debug("Failed to extract card from DOM", exc_info=True)
                continue

        return listings

    async def _scrape_page(self, url: str, operation: str) -> list[RawListing]:
        """Scrape a single search results page."""
        page = await self._new_page()
        listings: list[RawListing] = []

        try:
            logger.info("Fetching %s", url)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            if response and response.status == 403:
                logger.warning("Got 403 on %s — retrying with delay", url)
                await page.wait_for_timeout(random.randint(3000, 6000))
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            if response and response.status != 200:
                logger.error("Got status %d on %s", response.status, url)
                return []

            # Wait for content to load
            await page.wait_for_timeout(random.randint(2000, 4000))

            # Strategy 1: Try __NEXT_DATA__
            next_data = await self._extract_next_data(page)
            if next_data:
                listings = await self._extract_from_next_data(next_data, operation)
                if listings:
                    logger.info("Extracted %d listings from __NEXT_DATA__", len(listings))
                    return listings

            # Strategy 2: DOM extraction
            listings = await self._extract_from_dom(page, operation)
            logger.info("Extracted %d listings from DOM", len(listings))

        except Exception:
            logger.exception("Error scraping %s", url)
        finally:
            await page.close()

        return listings

    async def scrape_listings(
        self,
        operation: str = "sale",
        max_pages: int = 5,
        property_types: list[str] | None = None,
    ) -> list[RawListing]:
        """Scrape Zonaprop listings for Capital Federal.

        Args:
            operation: "sale" or "rent"
            max_pages: Number of result pages to scrape (each has ~20 listings).
            property_types: Filter by property types (default: deptos, casas, PH).

        Returns:
            List of extracted RawListing objects.
        """
        all_listings: list[RawListing] = []
        seen_ids: set[str] = set()

        for page_num in range(1, max_pages + 1):
            url = _build_search_url(operation, property_types, page_num)
            page_listings = await self._scrape_page(url, operation)

            if not page_listings:
                logger.info("No listings on page %d, stopping", page_num)
                break

            # Deduplicate within this run
            for listing in page_listings:
                if listing.external_id not in seen_ids:
                    seen_ids.add(listing.external_id)
                    all_listings.append(listing)

            logger.info(
                "Page %d/%d: %d new listings (total: %d)",
                page_num, max_pages, len(page_listings), len(all_listings),
            )

            # Random delay between pages
            if page_num < max_pages:
                import asyncio
                await asyncio.sleep(random.uniform(3, 7))

        return all_listings

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
