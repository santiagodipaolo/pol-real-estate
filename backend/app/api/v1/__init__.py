from fastapi import APIRouter

from app.api.v1.currency import router as currency_router
from app.api.v1.barrios import router as barrios_router
from app.api.v1.listings import router as listings_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.map import router as map_router

router = APIRouter()
router.include_router(currency_router, prefix="/currency", tags=["currency"])
router.include_router(barrios_router, prefix="/barrios", tags=["barrios"])
router.include_router(listings_router, prefix="/listings", tags=["listings"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
router.include_router(map_router, prefix="/map", tags=["map"])
