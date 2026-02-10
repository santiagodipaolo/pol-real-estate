from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.listing import ListingsPage, ListingDetail, ListingStats
from app.services.listing_service import get_listings, get_listing_by_id, get_listing_stats

router = APIRouter()


@router.get("", response_model=ListingsPage)
async def list_listings(
    operation_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    barrio_id: Optional[int] = Query(None),
    price_min: Optional[float] = Query(None),
    price_max: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    filters = {
        "operation_type": operation_type,
        "property_type": property_type,
        "barrio_id": barrio_id,
        "price_min": price_min,
        "price_max": price_max,
    }
    return await get_listings(db, filters, page, per_page)


@router.get("/stats", response_model=ListingStats)
async def stats(
    operation_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    barrio_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    filters = {
        "operation_type": operation_type,
        "property_type": property_type,
        "barrio_id": barrio_id,
    }
    return await get_listing_stats(db, filters)


@router.get("/{listing_id}", response_model=ListingDetail)
async def get_listing(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    return await get_listing_by_id(db, listing_id)
