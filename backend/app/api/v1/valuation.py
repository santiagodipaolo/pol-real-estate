"""Valuation API — estimate property prices using the ML model."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.valuation.model import ValuationModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton model instance — loaded once on first request
_model: ValuationModel | None = None


def _get_model() -> ValuationModel:
    global _model
    if _model is None:
        _model = ValuationModel()
        try:
            _model.load("valuation_sale_v1")
        except FileNotFoundError:
            raise HTTPException(
                status_code=503,
                detail="Valuation model not trained yet. Run: python -m scripts.train_model",
            )
    return _model


class ValuationRequest(BaseModel):
    surface_total_m2: float = Field(..., gt=0, description="Total surface in m²")
    surface_covered_m2: Optional[float] = Field(None, gt=0, description="Covered surface in m²")
    rooms: Optional[int] = Field(None, ge=1, description="Total rooms (ambientes)")
    bedrooms: Optional[int] = Field(None, ge=0, description="Bedrooms")
    bathrooms: Optional[int] = Field(None, ge=1, description="Bathrooms")
    garages: Optional[int] = Field(None, ge=0, description="Garage spots")
    age_years: Optional[int] = Field(None, ge=0, description="Building age in years")
    expenses_ars: Optional[float] = Field(None, ge=0, description="Monthly expenses in ARS")
    property_type: str = Field("Departamento", description="Property type")
    barrio_id: Optional[int] = Field(None, description="Barrio ID")
    barrio_name: Optional[str] = Field(None, description="Barrio name (alternative to barrio_id)")


class ValuationResponse(BaseModel):
    price_usd: float
    price_usd_low: float
    price_usd_high: float
    price_usd_m2: float
    price_usd_m2_low: float
    price_usd_m2_high: float
    surface_total_m2: float
    confidence: str


class ComparableItem(BaseModel):
    title: str
    url: str
    price_usd: float
    price_usd_m2: float
    surface_total_m2: float
    barrio: str
    rooms: int | None


class ValuationWithComparables(ValuationResponse):
    comparables: list[ComparableItem]


@router.post("/estimate", response_model=ValuationResponse)
async def estimate_value(req: ValuationRequest):
    """Estimate the market value of a property."""
    model = _get_model()

    # Resolve barrio_name to barrio_id if needed
    barrio_id = req.barrio_id
    if not barrio_id and req.barrio_name:
        # Look up barrio by name from the model's barrio_stats
        if model.barrio_stats is not None:
            from sqlalchemy import create_engine, select
            from sqlalchemy.orm import Session
            from app.core.config import settings
            from app.models.barrio import Barrio

            engine = create_engine(settings.sync_database_url)
            with Session(engine) as session:
                barrio = session.execute(
                    select(Barrio.id).where(Barrio.name.ilike(f"%{req.barrio_name}%"))
                ).scalar_one_or_none()
                barrio_id = barrio
            engine.dispose()

    pred = model.predict(
        surface_total_m2=req.surface_total_m2,
        surface_covered_m2=req.surface_covered_m2,
        rooms=req.rooms,
        bedrooms=req.bedrooms,
        bathrooms=req.bathrooms,
        garages=req.garages,
        age_years=req.age_years,
        expenses_ars=req.expenses_ars,
        property_type=req.property_type,
        barrio_id=barrio_id,
    )

    # Confidence level based on range width
    range_pct = (pred["price_usd_high"] - pred["price_usd_low"]) / pred["price_usd"] * 100
    if range_pct < 15:
        confidence = "high"
    elif range_pct < 30:
        confidence = "medium"
    else:
        confidence = "low"

    return ValuationResponse(
        **pred,
        confidence=confidence,
    )


@router.get("/metrics")
async def model_metrics():
    """Return current model training metrics."""
    model = _get_model()
    return model.metrics


@router.post("/reload")
async def reload_model():
    """Reload the model from disk (after retraining)."""
    global _model
    _model = None
    model = _get_model()
    return {"status": "reloaded", "samples": model.metrics.get("samples", 0)}
