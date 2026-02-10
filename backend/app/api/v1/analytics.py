from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.analytics import (
    PriceTrendPoint,
    RentalYieldBarrio,
    MarketPulse,
    PriceDistribution,
    ROISimulationRequest,
    ROISimulationResult,
)
from app.services.analytics_service import (
    get_price_trends,
    get_rental_yield,
    get_market_pulse,
    get_price_distribution,
    simulate_roi,
)

router = APIRouter()


@router.get("/price-trends", response_model=list[PriceTrendPoint])
async def price_trends(
    operation_type: str = Query("sale"),
    currency: str = Query("usd_blue"),
    inflation_adjusted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    return await get_price_trends(db, operation_type, currency, inflation_adjusted)


@router.get("/rental-yield", response_model=list[RentalYieldBarrio])
async def rental_yield(db: AsyncSession = Depends(get_db)):
    return await get_rental_yield(db)


@router.get("/market-pulse", response_model=MarketPulse)
async def market_pulse(db: AsyncSession = Depends(get_db)):
    return await get_market_pulse(db)


@router.get("/price-distribution", response_model=PriceDistribution)
async def price_distribution(
    barrio_id: Optional[int] = Query(None),
    bins: int = Query(30, ge=5, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await get_price_distribution(db, barrio_id, bins)


@router.post("/roi-simulation")
async def roi_simulation(request: ROISimulationRequest):
    return simulate_roi(request.model_dump())
