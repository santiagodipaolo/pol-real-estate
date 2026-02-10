from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.map import ChoroplethResponse, HeatmapResponse, ClusterResponse
from app.services.map_service import get_choropleth_data, get_heatmap_data, get_cluster_data

router = APIRouter()


@router.get("/choropleth")
async def choropleth(
    metric: str = Query("median_price_usd_m2", description="Metric to visualize"),
    operation_type: str = Query("sale"),
    db: AsyncSession = Depends(get_db),
):
    return await get_choropleth_data(db, metric, operation_type)


@router.get("/heatmap", response_model=HeatmapResponse)
async def heatmap(
    operation_type: str = Query("sale"),
    bbox: Optional[str] = Query(None, description="west,south,east,north"),
    db: AsyncSession = Depends(get_db),
):
    return await get_heatmap_data(db, operation_type, bbox)


@router.get("/clusters", response_model=ClusterResponse)
async def clusters(
    bbox: Optional[str] = Query(None, description="west,south,east,north"),
    zoom: int = Query(12, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    return await get_cluster_data(db, bbox, zoom)
