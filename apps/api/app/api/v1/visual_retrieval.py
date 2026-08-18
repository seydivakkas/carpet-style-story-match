"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Visual Retrieval API Router v1.0.0
"""
from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession


from app.db.session import get_db
from app.domain.visual_retrieval import (
    VisualRetrievalQuery,
    VisualRetrievalResponse,
    CatalogVisualMatch,
    HistoricalVisualMatch,
    CatalogCorpusAccounting,
    HistoricalCorpusAccounting,
    VisualRetrievalService,
    QuerySourceType,
    CANONICAL_STYLE_DNA_VERSION,
)

router = APIRouter(prefix="/visual-retrieval", tags=["Visual Retrieval"])


class VisualRetrievalApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style_dna: Union[Dict[str, float], List[Any]] = Field(
        ...,
        description="Exactly 9 canonical Style DNA dimensions with values in [0.0, 1.0]"
    )
    style_dna_version: str = Field(
        default=CANONICAL_STYLE_DNA_VERSION,
        description="Frozen Style DNA algorithm version"
    )
    top_k_catalog: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of top catalog visual matches to return (1-50)"
    )
    top_k_historical: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of top historical visual matches to return (1-50)"
    )
    query_id: Optional[str] = Field(default=None, description="Optional query identifier")
    query_source_type: QuerySourceType = Field(
        default=QuerySourceType.DIRECT_VECTOR,
        description="Provenance classification of input query vector"
    )
    exclude_id: Optional[str] = Field(
        default=None,
        description="Optional candidate or reference ID to exclude from self-matching"
    )


class CatalogRetrievalApiResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retrieval_version: str
    retrieval_policy_version: str
    query_provenance: Dict[str, Any]
    catalog_corpus_accounting: CatalogCorpusAccounting
    catalog_matches: List[CatalogVisualMatch]


class HistoricalRetrievalApiResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retrieval_version: str
    retrieval_policy_version: str
    query_provenance: Dict[str, Any]
    historical_corpus_accounting: HistoricalCorpusAccounting
    historical_matches: List[HistoricalVisualMatch]


@router.post(
    "",
    response_model=VisualRetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute dual-corpus visual proximity retrieval",
    description="Finds top visually similar catalog carpets and verified historical references based purely on 9D Style DNA proximity.",
)
async def execute_visual_retrieval(
    req: VisualRetrievalApiRequest,
    db: AsyncSession = Depends(get_db),
) -> VisualRetrievalResponse:
    try:
        query = VisualRetrievalQuery(
            style_dna=req.style_dna,
            style_dna_version=req.style_dna_version,
            query_id=req.query_id,
            query_source_type=req.query_source_type,
            exclude_id=req.exclude_id,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_RETRIEVAL_QUERY",
                "message": str(ve),
            },
        ) from ve

    service = VisualRetrievalService(db)

    try:
        response = await service.retrieve_both_async(
            query=query,
            top_k_catalog=req.top_k_catalog,
            top_k_historical=req.top_k_historical,
        )
        return response
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_RETRIEVAL_QUERY",
                "message": str(ve),
            },
        ) from ve


@router.post(
    "/catalog",
    response_model=CatalogRetrievalApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute catalog-only visual proximity retrieval",
)
async def execute_catalog_visual_retrieval(
    req: VisualRetrievalApiRequest,
    db: AsyncSession = Depends(get_db),
) -> CatalogRetrievalApiResponse:
    try:
        query = VisualRetrievalQuery(
            style_dna=req.style_dna,
            style_dna_version=req.style_dna_version,
            query_id=req.query_id,
            query_source_type=req.query_source_type,
            exclude_id=req.exclude_id,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_RETRIEVAL_QUERY",
                "message": str(ve),
            },
        ) from ve

    service = VisualRetrievalService(db)

    try:
        cat_matches, cat_accounting = await service.retrieve_catalog_async(query, req.top_k_catalog)
        return CatalogRetrievalApiResponse(
            retrieval_version="visual-retrieval-v1.0.0",
            retrieval_policy_version="visual-retrieval-policy-v1.0.0",
            query_provenance={
                "query_id": query.query_id,
                "query_source_type": query.query_source_type.value if hasattr(query.query_source_type, "value") else str(query.query_source_type),
                "style_dna_version": query.style_dna_version,
                "exclude_id": query.exclude_id,
            },
            catalog_corpus_accounting=cat_accounting,
            catalog_matches=cat_matches,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_RETRIEVAL_QUERY",
                "message": str(ve),
            },
        ) from ve


@router.post(
    "/historical",
    response_model=HistoricalRetrievalApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute historical-only visual proximity retrieval",
)
async def execute_historical_visual_retrieval(
    req: VisualRetrievalApiRequest,
    db: AsyncSession = Depends(get_db),
) -> HistoricalRetrievalApiResponse:
    try:
        query = VisualRetrievalQuery(
            style_dna=req.style_dna,
            style_dna_version=req.style_dna_version,
            query_id=req.query_id,
            query_source_type=req.query_source_type,
            exclude_id=req.exclude_id,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_RETRIEVAL_QUERY",
                "message": str(ve),
            },
        ) from ve

    service = VisualRetrievalService(db)

    try:
        hist_matches, hist_accounting = await service.retrieve_historical_async(query, req.top_k_historical)
        return HistoricalRetrievalApiResponse(
            retrieval_version="visual-retrieval-v1.0.0",
            retrieval_policy_version="visual-retrieval-policy-v1.0.0",
            query_provenance={
                "query_id": query.query_id,
                "query_source_type": query.query_source_type.value if hasattr(query.query_source_type, "value") else str(query.query_source_type),
                "style_dna_version": query.style_dna_version,
                "exclude_id": query.exclude_id,
            },
            historical_corpus_accounting=hist_accounting,
            historical_matches=hist_matches,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_RETRIEVAL_QUERY",
                "message": str(ve),
            },
        ) from ve
