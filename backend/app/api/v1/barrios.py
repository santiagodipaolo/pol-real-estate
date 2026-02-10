from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.barrio import BarrioWithStats, BarrioDetail, BarrioRanking, BarrioComparison
from app.schemas.analytics import PriceTrendPoint
from app.services.barrio_service import (
    get_all_barrios,
    get_barrio_by_slug,
    get_barrio_trends,
    compare_barrios,
    get_barrio_ranking,
)

router = APIRouter()


@router.get("", response_model=list[BarrioWithStats])
async def list_barrios(db: AsyncSession = Depends(get_db)):
    return await get_all_barrios(db)


@router.get("/compare", response_model=BarrioComparison)
async def compare(
    slugs: list[str] = Query(..., alias="slugs[]"),
    db: AsyncSession = Depends(get_db),
):
    return await compare_barrios(db, slugs)


@router.get("/ranking", response_model=list[BarrioRanking])
async def ranking(
    metric: str = Query("median_price_usd_m2"),
    operation_type: str = Query("sale"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    return await get_barrio_ranking(db, metric, operation_type, order)


@router.get("/{slug}", response_model=BarrioDetail)
async def get_barrio(slug: str, db: AsyncSession = Depends(get_db)):
    return await get_barrio_by_slug(db, slug)


@router.get("/{slug}/trends", response_model=list[PriceTrendPoint])
async def trends(
    slug: str,
    metric: str = Query("price_m2"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_barrio_trends(db, slug, metric, from_date, to_date)
