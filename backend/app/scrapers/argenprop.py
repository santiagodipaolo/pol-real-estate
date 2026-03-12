"""Argenprop scraper using Playwright.

Argenprop uses server-rendered HTML (no __NEXT_DATA__). Cards are extracted
from the DOM using CSS selectors.

Card structure:
  .listing__item > a.card[data-item-card="ID"]
    .card__price          → "USD 350.000 + $295.000 expensas"
    .card__address        → "Av Dr P Goyena 1600, Piso 12"
    .card__main-features  → li elements: "85 m² cubie.", "3 dorm.", "5 años"
    href                  → /departamento-en-venta-en-caballito-4-ambientes--6162584

Pagination: --pagina-{n}
"""

from __future__ import annotations

import logging
import random
import re
from typing import Any

from playwright.async_api import Browser, Page, Playwright, async_playwright

from app.scrapers.base import BaseScraper, RawListing

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.argenprop.com"

_OPERATION_SLUGS = {
    "sale": "venta",
    "rent": "alquiler",
}

_PROPERTY_TYPE_FROM_URL = {
    "departamento": "Departamento",
    "casa": "Casa",
    "ph": "PH",
    "local": "Local",
    "oficina": "Oficina",
    "terreno": "Terreno",
    "cochera": "Cochera",
}

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


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
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _build_search_url(operation: str, page: int = 1) -> str:
    op_slug = _OPERATION_SLUGS.get(operation, "venta")
    page_suffix = f"--pagina-{page}" if page > 1 else ""
    return f"{_BASE_URL}/departamento-y-casa-y-ph-en-{op_slug}-en-capital-federal{page_suffix}"


def _parse_price(price_text: str) -> tuple[float | None, str, float | None]:
    """Parse price text like 'USD 350.000 + $295.000 expensas'.

    Returns (price, currency, expenses_ars).
    """
    if not price_text:
        return None, "USD", None

    price = None
    currency = "USD"
    expenses = None

    # Split on '+' to separate price from expenses
    parts = price_text.split("+")

    # Main price
    main = parts[0].strip()
    if "USD" in main or "U$S" in main:
        currency = "USD"
    elif "$" in main:
        currency = "ARS"

    # Extract number: remove dots (thousands), handle commas
    nums = re.findall(r"[\d]+(?:\.[\d]{3})*(?:,\d+)?", main)
    if nums:
        price = _safe_float(nums[0].replace(".", "").replace(",", "."))

    # Expenses
    if len(parts) > 1:
        exp_part = parts[1].strip()
        exp_nums = re.findall(r"[\d]+(?:\.[\d]{3})*(?:,\d+)?", exp_part)
        if exp_nums:
            expenses = _safe_float(exp_nums[0].replace(".", "").replace(",", "."))

    return price, currency, expenses


def _parse_features(feat_texts: list[str]) -> dict:
    """Parse feature texts like ['85 m² cubie.', '3 dorm.', '5 años'].

    Returns dict with surface, bedrooms, bathrooms, age, garages.
    """
    result: dict[str, Any] = {}
    seen = set()

    for text in feat_texts:
        t = text.strip().lower()
        if t in seen:
            continue
        seen.add(t)

        nums = re.findall(r"[\d]+(?:[.,]\d+)?", t)
        num = _safe_float(nums[0].replace(",", ".")) if nums else None

        if ("m²" in t or "m2" in t) and num:
            if "cub" in t:
                result["surface_covered_m2"] = num
            elif "tot" in t:
                result["surface_total_m2"] = num
            else:
                # Generic m² — use as covered if no qualifier
                result.setdefault("surface_covered_m2", num)
        elif "dorm" in t and num:
            result["bedrooms"] = _safe_int(num)
        elif ("baño" in t or "bano" in t) and num:
            result["bathrooms"] = _safe_int(num)
        elif ("año" in t or "ano" in t) and num:
            result["age_years"] = _safe_int(num)
        elif ("coch" in t or "garage" in t) and num:
            result["garages"] = _safe_int(num)

    return result


def _property_type_from_href(href: str) -> str:
    """Extract property type from URL like /departamento-en-venta-..."""
    href_lower = href.lower()
    for key, value in _PROPERTY_TYPE_FROM_URL.items():
        if href_lower.startswith(f"/{key}"):
            return value
    return "Departamento"


def _rooms_from_href(href: str) -> int | None:
    """Extract rooms (ambientes) from URL like ...-4-ambientes--123"""
    match = re.search(r"-(\d+)-ambientes?", href)
    return int(match.group(1)) if match else None


def _barrio_from_href(href: str) -> str | None:
    """Extract barrio from URL like /departamento-en-venta-en-caballito-4-ambientes--123"""
    # Match: -en-{operation}-en-{barrio}-
    match = re.search(r"-en-(?:venta|alquiler)-en-([a-z-]+?)(?:-\d+-ambientes|--\d)", href)
    if match:
        barrio = match.group(1).replace("-", " ").title()
        return barrio
    return None


class ArgenpropScraper(BaseScraper):
    """Scraper for argenprop.com using Playwright."""

    source_name = "argenprop"

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def _ensure_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
        return self._browser

    async def _new_page(self) -> Page:
        browser = await self._ensure_browser()
        context = await browser.new_context(
            user_agent=random.choice(_USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-AR,es;q=0.9,en;q=0.7",
                "DNT": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        page = await context.new_page()

        # Stealth
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            window.chrome = {runtime: {}};
        """)

        # Block images and fonts
        await page.route(
            re.compile(r"\.(png|jpg|jpeg|gif|webp|svg|woff|woff2|ttf)$"),
            lambda route: route.abort(),
        )

        return page

    async def _extract_from_dom(self, page: Page, operation: str) -> list[RawListing]:
        """Extract listings from DOM."""
        listings: list[RawListing] = []

        cards = await page.query_selector_all(".listing__item")
        if not cards:
            return []

        for card in cards:
            try:
                link = await card.query_selector("a.card")
                if not link:
                    continue

                # ID and URL
                item_id = await link.get_attribute("data-item-card")
                href = await link.get_attribute("href") or ""
                if not item_id:
                    continue

                url = f"{_BASE_URL}{href}" if not href.startswith("http") else href

                # Price
                price_el = await card.query_selector(".card__price")
                price_text = (await price_el.inner_text()).strip() if price_el else ""
                price, currency, expenses = _parse_price(price_text)

                # Address
                addr_el = await card.query_selector(".card__address")
                address = (await addr_el.inner_text()).strip() if addr_el else None

                # Title
                title_el = await card.query_selector(".card__title")
                title = (await title_el.inner_text()).strip() if title_el else ""

                # Features
                feat_els = await card.query_selector_all(".card__main-features li")
                feat_texts = []
                for fel in feat_els:
                    t = (await fel.inner_text()).strip()
                    if t:
                        feat_texts.append(t)
                features = _parse_features(feat_texts)

                # Property type and rooms from URL
                prop_type = _property_type_from_href(href)
                rooms = _rooms_from_href(href)

                # Barrio from URL
                barrio = _barrio_from_href(href)

                # Use covered surface as total if total not available
                surface_total = features.get("surface_total_m2") or features.get("surface_covered_m2")
                surface_covered = features.get("surface_covered_m2")

                listings.append(RawListing(
                    external_id=item_id,
                    source="argenprop",
                    url=url,
                    title=title,
                    operation_type=operation,
                    property_type=prop_type,
                    price=price,
                    currency=currency,
                    expenses_ars=expenses,
                    surface_total_m2=surface_total,
                    surface_covered_m2=surface_covered,
                    rooms=rooms,
                    bedrooms=features.get("bedrooms"),
                    bathrooms=features.get("bathrooms"),
                    garages=features.get("garages"),
                    age_years=features.get("age_years"),
                    address=address,
                    barrio_name=barrio,
                ))
            except Exception:
                logger.debug("Failed to extract Argenprop card", exc_info=True)
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

            if response and response.status not in (200, 202):
                logger.error("Got status %d on %s", response.status, url)
                return []

            await page.wait_for_timeout(random.randint(2000, 4000))
            listings = await self._extract_from_dom(page, operation)
            logger.info("Extracted %d listings from Argenprop DOM", len(listings))

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
        """Scrape Argenprop listings for Capital Federal."""
        all_listings: list[RawListing] = []
        seen_ids: set[str] = set()

        for page_num in range(1, max_pages + 1):
            url = _build_search_url(operation, page_num)
            page_listings = await self._scrape_page(url, operation)

            if not page_listings:
                logger.info("No listings on page %d, stopping", page_num)
                break

            for listing in page_listings:
                if listing.external_id not in seen_ids:
                    seen_ids.add(listing.external_id)
                    all_listings.append(listing)

            logger.info(
                "Page %d/%d: %d new listings (total: %d)",
                page_num, max_pages, len(page_listings), len(all_listings),
            )

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
