"""Detail scraping data structures and parsing helpers.

DetailData holds enriched data extracted from individual listing pages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DetailData:
    """Enriched data from an individual listing page."""

    floor: int | None = None
    orientation: str | None = None  # "N", "S", "E", "W", "NE", "NO", "SE", "SO"
    condition: str | None = None  # "Nuevo", "Excelente", "Bueno", "Regular", "A reciclar"
    description: str | None = None
    amenities: dict[str, bool] = field(default_factory=dict)
    latitude: float | None = None
    longitude: float | None = None
    surface_total_m2: float | None = None
    surface_covered_m2: float | None = None
    bathrooms: int | None = None
    garages: int | None = None
    expenses_ars: float | None = None


# Canonical amenity keys and their detection patterns
_AMENITY_PATTERNS: dict[str, list[str]] = {
    "pool": ["pileta", "piscina", "swimming"],
    "gym": ["gimnasio", "gym", "fitness"],
    "security": ["seguridad", "vigilancia", "guardia", "vigilador"],
    "balcony": ["balcón", "balcon", "terraza"],
    "laundry": ["lavadero", "laundry"],
    "rooftop": ["terraza", "rooftop", "azotea"],
    "sum": ["sum", "salón de usos", "salon de usos", "salon de fiestas"],
    "solarium": ["solarium", "solárium"],
    "parking": ["cochera", "estacionamiento", "garage", "parking"],
    "storage": ["baulera", "depósito", "deposito"],
    "elevator": ["ascensor", "elevador"],
    "ac": ["aire acondicionado", "a/c", "aire frio"],
    "heating": ["calefacción", "calefaccion", "losa radiante"],
}


def parse_amenities_from_text(texts: list[str]) -> dict[str, bool]:
    """Parse a list of amenity strings into a canonical dict.

    Args:
        texts: Raw amenity strings from the listing page.

    Returns:
        Dict like {"pool": true, "gym": false, ...}
    """
    combined = " ".join(t.lower() for t in texts)
    result: dict[str, bool] = {}
    for amenity, patterns in _AMENITY_PATTERNS.items():
        result[amenity] = any(p in combined for p in patterns)
    return result


_FLOOR_PATTERNS = [
    re.compile(r"piso\s*(\d{1,2})", re.IGNORECASE),
    re.compile(r"(\d{1,2})[°ºª]\s*piso", re.IGNORECASE),
    re.compile(r"(\d{1,2})(?:er|do|to|vo|no|mo)\s*piso", re.IGNORECASE),
    re.compile(r"piso:\s*(\d{1,2})", re.IGNORECASE),
]


def parse_floor(text: str) -> int | None:
    """Extract floor number from text like 'Piso 5', '3° piso', etc."""
    if not text:
        return None
    text_lower = text.lower()
    if "planta baja" in text_lower or "pb" == text_lower.strip():
        return 0
    for pattern in _FLOOR_PATTERNS:
        match = pattern.search(text)
        if match:
            val = int(match.group(1))
            if 0 <= val <= 60:
                return val
    return None


_CONDITION_MAP = {
    "a estrenar": "Nuevo",
    "nuevo": "Nuevo",
    "excelente": "Excelente",
    "muy bueno": "Muy bueno",
    "bueno": "Bueno",
    "regular": "Regular",
    "a reciclar": "A reciclar",
    "a refaccionar": "A reciclar",
    "en construcción": "En construccion",
    "en construccion": "En construccion",
    "pozo": "En construccion",
}


def parse_condition(text: str) -> str | None:
    """Normalize condition text to a canonical value."""
    if not text:
        return None
    text_lower = text.strip().lower()
    for key, value in _CONDITION_MAP.items():
        if key in text_lower:
            return value
    return None


_ORIENTATION_MAP = {
    "norte": "N",
    "sur": "S",
    "este": "E",
    "oeste": "W",
    "noreste": "NE",
    "noroeste": "NO",
    "sudeste": "SE",
    "sudoeste": "SO",
    "sureste": "SE",
    "suroeste": "SO",
    "contrafrente": "contrafrente",
    "frente": "frente",
}


def parse_orientation(text: str) -> str | None:
    """Parse orientation from text like 'Norte', 'Frente', 'NE'."""
    if not text:
        return None
    text_lower = text.strip().lower()
    for key, value in _ORIENTATION_MAP.items():
        if key in text_lower:
            return value
    # Direct abbreviation match
    abbrevs = {"n", "s", "e", "w", "ne", "no", "se", "so", "nw", "sw"}
    if text_lower in abbrevs:
        return text.upper()
    return None
