"""
Taxonomies & Upload Analysis Contract Discovery API Endpoints.
Provides read-only discovery of visual categories, motif ontology, and contract schema.
No real AI inference is performed in these endpoints.
"""
from fastapi import APIRouter, status
from typing import Dict, Any

from app.domain.upload_analysis.visual_categories import (
    CANONICAL_VISUAL_CATEGORIES,
    VISUAL_CATEGORY_TAXONOMY_VERSION
)
from app.domain.upload_analysis.motif_ontology import (
    MOTIF_ONTOLOGY_DEFINITIONS,
    MOTIF_ONTOLOGY_VERSION,
    CANONICAL_PRODUCTION_MOTIFS
)
from app.domain.upload_analysis.schemas import (
    UploadAnalysisResult,
    UPLOAD_ANALYSIS_SCHEMA_VERSION
)

router = APIRouter(tags=["taxonomies"])


@router.get(
    "/taxonomies/visual-categories",
    status_code=status.HTTP_200_OK,
    summary="Get Visual Category Taxonomy v1"
)
async def get_visual_category_taxonomy() -> Dict[str, Any]:
    return {
        "taxonomy_version": VISUAL_CATEGORY_TAXONOMY_VERSION,
        "total_categories": len(CANONICAL_VISUAL_CATEGORIES),
        "categories": CANONICAL_VISUAL_CATEGORIES
    }


@router.get(
    "/taxonomies/motifs",
    status_code=status.HTTP_200_OK,
    summary="Get Motif Ontology v1"
)
async def get_motif_ontology() -> Dict[str, Any]:
    return {
        "ontology_version": MOTIF_ONTOLOGY_VERSION,
        "total_motifs": len(MOTIF_ONTOLOGY_DEFINITIONS),
        "canonical_production_motifs": CANONICAL_PRODUCTION_MOTIFS,
        "motifs": MOTIF_ONTOLOGY_DEFINITIONS
    }


@router.get(
    "/upload-analysis/schema",
    status_code=status.HTTP_200_OK,
    summary="Get User Upload Analysis Contract Schema"
)
async def get_upload_analysis_schema() -> Dict[str, Any]:
    return {
        "schema_version": UPLOAD_ANALYSIS_SCHEMA_VERSION,
        "visual_category_taxonomy_version": VISUAL_CATEGORY_TAXONOMY_VERSION,
        "motif_ontology_version": MOTIF_ONTOLOGY_VERSION,
        "json_schema": UploadAnalysisResult.model_json_schema()
    }
