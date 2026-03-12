"""Opportunities API — opportunity score + analyze URL."""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.barrio import Barrio
from app.valuation.model import ValuationModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Reuse the valuation model singleton
_model: ValuationModel | None = None


def _get_model() -> ValuationModel:
    global _model
    if _model is None:
        _model = ValuationModel()
        try:
            _model.load("valuation_sale_v1")
        except FileNotFoundError:
            raise HTTPException(503, "Valuation model not trained yet")
    return _model


def _compute_opportunity_score(
    listed_price_usd_m2: float,
    estimated_price_usd_m2: float,
    estimated_low: float,
    estimated_high: float,
) -> dict:
    """Compute opportunity score for a listing.

    Returns dict with score (0-100), discount_pct, and verdict.
    """
    if estimated_price_usd_m2 <= 0:
        return {"score": 50, "discount_pct": 0, "verdict": "sin_datos"}

    discount_pct = (estimated_price_usd_m2 - listed_price_usd_m2) / estimated_price_usd_m2 * 100

    # Score: 0-100 where 100 = best opportunity
    if listed_price_usd_m2 <= estimated_low:
        score = 80 + min(20, discount_pct * 0.5)
    elif listed_price_usd_m2 <= estimated_price_usd_m2:
        ratio = (estimated_price_usd_m2 - listed_price_usd_m2) / max(1, estimated_price_usd_m2 - estimated_low)
        score = 60 + ratio * 20
    elif listed_price_usd_m2 <= estimated_high:
        ratio = (listed_price_usd_m2 - estimated_price_usd_m2) / max(1, estimated_high - estimated_price_usd_m2)
        score = 60 - ratio * 20
    else:
        overprice = (listed_price_usd_m2 - estimated_high) / estimated_high * 100
        score = max(0, 40 - overprice)

    score = max(0, min(100, score))

    if score >= 75:
        verdict = "oportunidad"
    elif score >= 55:
        verdict = "precio_justo"
    elif score >= 35:
        verdict = "caro"
    else:
        verdict = "sobrepreciado"

    return {
        "score": round(score, 1),
        "discount_pct": round(discount_pct, 1),
        "verdict": verdict,
    }


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class OpportunityScoreItem(BaseModel):
    listing_id: str
    url: Optional[str] = None
    title: Optional[str] = None
    barrio_name: Optional[str] = None
    property_type: str
    surface_total_m2: float
    rooms: Optional[int] = None
    listed_price_usd: float
    listed_price_usd_m2: float
    estimated_price_usd: float
    estimated_price_usd_m2: float
    estimated_low: float
    estimated_high: float
    score: float
    discount_pct: float
    verdict: str


class OpportunityScoredResponse(BaseModel):
    items: list[OpportunityScoreItem]
    total: int
    avg_score: float
    best_barrio: Optional[str] = None


class AnalyzeURLRequest(BaseModel):
    url: str = Field(..., description="Zonaprop listing URL to analyze")


class AnalyzeURLResponse(BaseModel):
    url: str
    title: Optional[str] = None
    barrio_name: Optional[str] = None
    property_type: str
    operation_type: str
    surface_total_m2: Optional[float] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    garages: Optional[int] = None
    listed_price_usd: Optional[float] = None
    listed_price_usd_m2: Optional[float] = None
    estimated_price_usd: Optional[float] = None
    estimated_price_usd_m2: Optional[float] = None
    estimated_low: Optional[float] = None
    estimated_high: Optional[float] = None
    score: Optional[float] = None
    discount_pct: Optional[float] = None
    verdict: Optional[str] = None
    confidence: Optional[str] = None


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.get("/scored", response_model=OpportunityScoredResponse)
async def get_scored_opportunities(
    operation_type: str = Query("sale"),
    min_score: float = Query(60, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
):
    """Get listings scored by opportunity (ML-based comparison)."""
    model = _get_model()
    engine = create_engine(settings.sync_database_url)

    items: list[OpportunityScoreItem] = []

    with Session(engine) as session:
        rows = session.execute(
            text("""
                SELECT l.id, l.url, l.title, b.name as barrio_name,
                       l.property_type, l.surface_total_m2, l.surface_covered_m2,
                       l.rooms, l.bedrooms, l.bathrooms, l.garages,
                       l.age_years, l.expenses_ars, l.price_usd_blue,
                       l.barrio_id, l.latitude, l.longitude
                FROM listings l
                LEFT JOIN barrios b ON l.barrio_id = b.id
                WHERE l.is_active = true
                  AND l.operation_type = :op
                  AND l.price_usd_blue IS NOT NULL
                  AND l.surface_total_m2 IS NOT NULL
                  AND l.surface_total_m2 > 10
                  AND l.price_usd_blue > 0
                ORDER BY l.last_seen_at DESC
                LIMIT 500
            """),
            {"op": operation_type},
        ).fetchall()

    engine.dispose()

    for row in rows:
        try:
            surface = float(row.surface_total_m2)
            price_usd = float(row.price_usd_blue)
            price_m2 = price_usd / surface

            pred = model.predict(
                surface_total_m2=surface,
                surface_covered_m2=float(row.surface_covered_m2) if row.surface_covered_m2 else None,
                rooms=row.rooms,
                bedrooms=row.bedrooms,
                bathrooms=row.bathrooms,
                garages=row.garages,
                age_years=row.age_years,
                expenses_ars=float(row.expenses_ars) if row.expenses_ars else None,
                property_type=row.property_type,
                barrio_id=row.barrio_id,
                latitude=float(row.latitude) if row.latitude else None,
                longitude=float(row.longitude) if row.longitude else None,
            )

            opp = _compute_opportunity_score(
                price_m2,
                pred["price_usd_m2"],
                pred["price_usd_m2_low"],
                pred["price_usd_m2_high"],
            )

            if opp["score"] >= min_score:
                items.append(OpportunityScoreItem(
                    listing_id=str(row.id),
                    url=row.url,
                    title=row.title,
                    barrio_name=row.barrio_name,
                    property_type=row.property_type,
                    surface_total_m2=surface,
                    rooms=row.rooms,
                    listed_price_usd=price_usd,
                    listed_price_usd_m2=round(price_m2, 0),
                    estimated_price_usd=pred["price_usd"],
                    estimated_price_usd_m2=pred["price_usd_m2"],
                    estimated_low=pred["price_usd_low"],
                    estimated_high=pred["price_usd_high"],
                    score=opp["score"],
                    discount_pct=opp["discount_pct"],
                    verdict=opp["verdict"],
                ))
        except Exception:
            continue

    items.sort(key=lambda x: x.score, reverse=True)
    items = items[:limit]

    avg_score = sum(i.score for i in items) / len(items) if items else 0

    barrio_counts: dict[str, int] = {}
    for i in items:
        if i.barrio_name:
            barrio_counts[i.barrio_name] = barrio_counts.get(i.barrio_name, 0) + 1
    best_barrio = max(barrio_counts, key=barrio_counts.get) if barrio_counts else None

    return OpportunityScoredResponse(
        items=items,
        total=len(items),
        avg_score=round(avg_score, 1),
        best_barrio=best_barrio,
    )


@router.post("/analyze-url", response_model=AnalyzeURLResponse)
async def analyze_url(req: AnalyzeURLRequest):
    """Scrape a single Zonaprop URL and return valuation + opportunity score."""
    url = req.url.strip()

    if "zonaprop.com.ar" not in url:
        raise HTTPException(400, "Only Zonaprop URLs are supported")

    from app.scrapers.zonaprop import ZonapropScraper

    scraper = ZonapropScraper(headless=True)
    try:
        page = await scraper._new_page()
        try:
            logger.info("Analyzing URL: %s", url)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            if not response or response.status != 200:
                raise HTTPException(502, f"Could not fetch URL (status {response.status if response else 'none'})")

            await page.wait_for_timeout(3000)

            url_lower = url.lower()
            operation = "rent" if "alquiler" in url_lower else "sale"

            title = None
            price = None
            currency = "USD"
            surface_total = None
            surface_covered = None
            rooms = None
            bedrooms = None
            bathrooms = None
            garages = None
            expenses = None
            barrio_name = None
            property_type = "Departamento"

            # Title
            title_el = await page.query_selector("h1")
            if title_el:
                title = (await title_el.inner_text()).strip()

            # Price — try multiple selectors
            for selector in ['[data-qa="POSTING_CARD_PRICE"]', '.price-items', '.price-tag', 'div.prices-and-fees__price']:
                price_el = await page.query_selector(selector)
                if price_el:
                    price_text = (await price_el.inner_text()).strip()
                    if "USD" in price_text or "U$S" in price_text:
                        currency = "USD"
                    elif "$" in price_text:
                        currency = "ARS"
                    clean = price_text.replace(".", "").replace(",", ".")
                    numbers = re.findall(r"[\d]+(?:\.[\d]+)?", clean)
                    if numbers:
                        price = float(numbers[0])
                        break

            # Features — try multiple selectors
            for feat_selector in ['li[data-qa]', '.technical-sheet li', '.property-features li', '.posting-features li']:
                feature_els = await page.query_selector_all(feat_selector)
                if feature_els:
                    for feat_el in feature_els:
                        text = (await feat_el.inner_text()).strip().lower()
                        nums = re.findall(r"[\d]+(?:[.,][\d]+)?", text)
                        num = float(nums[0].replace(",", ".")) if nums else None

                        if "m² tot" in text and num:
                            surface_total = num
                        elif "m² cub" in text and num:
                            surface_covered = num
                        elif "m²" in text and num and not surface_total:
                            surface_total = num
                        elif "amb" in text and num:
                            rooms = int(num)
                        elif ("dorm" in text or "hab" in text) and num:
                            bedrooms = int(num)
                        elif "baño" in text and num:
                            bathrooms = int(num)
                        elif ("coch" in text or "garage" in text) and num:
                            garages = int(num)
                        elif "expensa" in text and num:
                            expenses = num
                    if surface_total:
                        break

            # Location
            for loc_selector in ['[data-qa="POSTING_CARD_LOCATION"]', '.posting-location', '.location-container h2', 'h2.title-location']:
                loc_el = await page.query_selector(loc_selector)
                if loc_el:
                    loc_text = (await loc_el.inner_text()).strip()
                    barrio_name = loc_text.split(",")[0].strip()
                    break

            # Property type from URL
            if "casa" in url_lower:
                property_type = "Casa"
            elif "ph-" in url_lower:
                property_type = "PH"

        finally:
            await page.close()
    finally:
        await scraper.close()

    # Compute valuation
    estimated_price_usd = None
    estimated_price_usd_m2 = None
    estimated_low = None
    estimated_high = None
    score = None
    discount_pct = None
    verdict = None
    confidence = None

    if surface_total and surface_total > 10 and operation == "sale":
        try:
            model = _get_model()

            barrio_id = None
            if barrio_name:
                engine = create_engine(settings.sync_database_url)
                with Session(engine) as session:
                    barrio_id = session.execute(
                        select(Barrio.id).where(Barrio.name.ilike(f"%{barrio_name}%"))
                    ).scalar_one_or_none()
                engine.dispose()

            pred = model.predict(
                surface_total_m2=surface_total,
                surface_covered_m2=surface_covered,
                rooms=rooms,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                garages=garages,
                expenses_ars=expenses,
                property_type=property_type,
                barrio_id=barrio_id,
            )

            estimated_price_usd = pred["price_usd"]
            estimated_price_usd_m2 = pred["price_usd_m2"]
            estimated_low = pred["price_usd_low"]
            estimated_high = pred["price_usd_high"]

            range_pct = (pred["price_usd_high"] - pred["price_usd_low"]) / pred["price_usd"] * 100 if pred["price_usd"] > 0 else 100
            confidence = "high" if range_pct < 15 else "medium" if range_pct < 30 else "low"

            if price and currency == "USD":
                listed_m2 = price / surface_total
                opp = _compute_opportunity_score(
                    listed_m2,
                    pred["price_usd_m2"],
                    pred["price_usd_m2_low"],
                    pred["price_usd_m2_high"],
                )
                score = opp["score"]
                discount_pct = opp["discount_pct"]
                verdict = opp["verdict"]
        except Exception:
            logger.exception("Failed to compute valuation for URL")

    listed_m2 = None
    if price and surface_total and surface_total > 0 and currency == "USD":
        listed_m2 = round(price / surface_total, 0)

    return AnalyzeURLResponse(
        url=url,
        title=title,
        barrio_name=barrio_name,
        property_type=property_type,
        operation_type=operation,
        surface_total_m2=surface_total,
        rooms=rooms,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        garages=garages,
        listed_price_usd=price if currency == "USD" else None,
        listed_price_usd_m2=listed_m2,
        estimated_price_usd=estimated_price_usd,
        estimated_price_usd_m2=estimated_price_usd_m2,
        estimated_low=estimated_low,
        estimated_high=estimated_high,
        score=score,
        discount_pct=discount_pct,
        verdict=verdict,
        confidence=confidence,
    )
