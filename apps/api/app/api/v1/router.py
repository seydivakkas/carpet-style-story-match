from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.meta import router as meta_router
from app.api.v1.carpets import router as carpets_router
from app.api.v1.carpet_images import router as carpet_images_router
from app.api.v1.style_dna import router as style_dna_router
from app.api.v1.preference_assessments import router as preference_assessments_router
from app.api.v1.motif_knowledge import router as motif_knowledge_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(meta_router)
api_v1_router.include_router(carpets_router)
api_v1_router.include_router(carpet_images_router)
api_v1_router.include_router(style_dna_router)
api_v1_router.include_router(preference_assessments_router)
api_v1_router.include_router(motif_knowledge_router)
