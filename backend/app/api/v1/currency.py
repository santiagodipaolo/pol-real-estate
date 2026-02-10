from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.currency import CurrencyRatesAll, CurrencyHistory
from app.services.currency_service import get_latest_rates, get_rate_history

router = APIRouter()


@router.get("/rates", response_model=CurrencyRatesAll)
async def get_rates(db: AsyncSession = Depends(get_db)):
    return await get_latest_rates(db)


@router.get("/rates/history", response_model=CurrencyHistory)
async def get_history(
    type: str = Query("blue", description="Rate type: blue, official, mep, ccl"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_rate_history(db, type, from_date, to_date)
