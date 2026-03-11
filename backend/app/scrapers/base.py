"""Base scraper interface for real estate portals."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class RawListing:
    """Normalized listing data extracted from any portal."""

    external_id: str
    source: str
    url: str
    title: str
    operation_type: str  # "sale" or "rent"
    property_type: str  # "Departamento", "Casa", "PH", etc.
    price: float | None = None
    currency: str = "USD"  # "USD" or "ARS"
    expenses_ars: float | None = None
    surface_total_m2: float | None = None
    surface_covered_m2: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    garages: int | None = None
    age_years: int | None = None
    amenities: list[str] = field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    barrio_name: str | None = None
    description: str | None = None
    images: list[str] = field(default_factory=list)
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseScraper(ABC):
    """Abstract base class for real estate portal scrapers."""

    source_name: str = "unknown"

    @abstractmethod
    async def scrape_listings(
        self,
        operation: str,
        max_pages: int = 5,
    ) -> list[RawListing]:
        """Scrape listings from the portal.

        Args:
            operation: "sale" or "rent"
            max_pages: Maximum number of result pages to scrape.

        Returns:
            List of RawListing objects.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources (browser, connections, etc)."""
        ...
