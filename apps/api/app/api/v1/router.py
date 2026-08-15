from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.meta import router as meta_router
from app.api.v1.carpets import router as carpets_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(meta_router)
api_v1_router.include_router(carpets_router)

