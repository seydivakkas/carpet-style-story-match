"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Visual Retrieval Service v1.0.0
"""
from typing import List, Tuple, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession


import logging

from app.domain.visual_retrieval.models import (
    CANONICAL_STYLE_DNA_VERSION,
    CANONICAL_RETRIEVAL_VERSION,
    CANONICAL_POLICY_VERSION,
    VisualRetrievalQuery,
    CatalogVisualMatch,
    HistoricalVisualMatch,
    CatalogCorpusAccounting,
    HistoricalCorpusAccounting,
    VisualRetrievalResponse,
)
from app.domain.visual_retrieval.distance import compute_9d_distance_and_score
from app.domain.visual_retrieval.corpus import (
    CatalogVisualCorpusProvider,
    HistoricalVisualCorpusProvider,
)

logger = logging.getLogger(__name__)


class VisualRetrievalService:
    """Orchestrates 9D Style DNA visual proximity retrieval for catalog and historical corpora."""

    def __init__(self, db: Union[AsyncSession, Session], min_proximity_pct: Optional[float] = None):
        self.db = db
        self.is_async = isinstance(db, AsyncSession)
        if min_proximity_pct is not None:
            self.min_proximity_pct = float(min_proximity_pct)
        else:
            try:
                from app.core.config import settings
                self.min_proximity_pct = float(getattr(settings, "RETRIEVAL_MIN_PROXIMITY_PCT", 30.0))
            except Exception:
                self.min_proximity_pct = 30.0

    async def retrieve_catalog_async(
        self,
        query: VisualRetrievalQuery,
        top_k: int = 5,
    ) -> Tuple[List[CatalogVisualMatch], CatalogCorpusAccounting]:
        if top_k < 1 or top_k > 50:
            raise ValueError(f"top_k_catalog must be between 1 and 50 inclusive, got {top_k}.")

        candidates, accounting = await CatalogVisualCorpusProvider.load_eligible_corpus_async(self.db)
        matches = self._rank_catalog_candidates(query, candidates, top_k)
        return matches, accounting

    def retrieve_catalog_sync(
        self,
        query: VisualRetrievalQuery,
        top_k: int = 5,
    ) -> Tuple[List[CatalogVisualMatch], CatalogCorpusAccounting]:
        if top_k < 1 or top_k > 50:
            raise ValueError(f"top_k_catalog must be between 1 and 50 inclusive, got {top_k}.")

        candidates, accounting = CatalogVisualCorpusProvider.load_eligible_corpus_sync(self.db)
        matches = self._rank_catalog_candidates(query, candidates, top_k)
        return matches, accounting

    async def retrieve_historical_async(
        self,
        query: VisualRetrievalQuery,
        top_k: int = 5,
    ) -> Tuple[List[HistoricalVisualMatch], HistoricalCorpusAccounting]:
        if top_k < 1 or top_k > 50:
            raise ValueError(f"top_k_historical must be between 1 and 50 inclusive, got {top_k}.")

        candidates, accounting = await HistoricalVisualCorpusProvider.load_eligible_corpus_async(self.db)
        matches = self._rank_historical_candidates(query, candidates, top_k)
        return matches, accounting

    def retrieve_historical_sync(
        self,
        query: VisualRetrievalQuery,
        top_k: int = 5,
    ) -> Tuple[List[HistoricalVisualMatch], HistoricalCorpusAccounting]:
        if top_k < 1 or top_k > 50:
            raise ValueError(f"top_k_historical must be between 1 and 50 inclusive, got {top_k}.")

        candidates, accounting = HistoricalVisualCorpusProvider.load_eligible_corpus_sync(self.db)
        matches = self._rank_historical_candidates(query, candidates, top_k)
        return matches, accounting

    async def retrieve_both_async(
        self,
        query: VisualRetrievalQuery,
        top_k_catalog: int = 5,
        top_k_historical: int = 5,
    ) -> VisualRetrievalResponse:
        cat_matches, cat_accounting = await self.retrieve_catalog_async(query, top_k_catalog)
        hist_matches, hist_accounting = await self.retrieve_historical_async(query, top_k_historical)

        query_prov = {
            "query_id": query.query_id,
            "query_source_type": query.query_source_type.value if hasattr(query.query_source_type, "value") else str(query.query_source_type),
            "style_dna_version": query.style_dna_version,
            "exclude_id": query.exclude_id,
        }

        return VisualRetrievalResponse(
            retrieval_version=CANONICAL_RETRIEVAL_VERSION,
            retrieval_policy_version=CANONICAL_POLICY_VERSION,
            query_provenance=query_prov,
            catalog_corpus_accounting=cat_accounting,
            historical_corpus_accounting=hist_accounting,
            catalog_matches=cat_matches,
            historical_matches=hist_matches,
        )

    def retrieve_both_sync(
        self,
        query: VisualRetrievalQuery,
        top_k_catalog: int = 5,
        top_k_historical: int = 5,
    ) -> VisualRetrievalResponse:
        cat_matches, cat_accounting = self.retrieve_catalog_sync(query, top_k_catalog)
        hist_matches, hist_accounting = self.retrieve_historical_sync(query, top_k_historical)

        query_prov = {
            "query_id": query.query_id,
            "query_source_type": query.query_source_type.value if hasattr(query.query_source_type, "value") else str(query.query_source_type),
            "style_dna_version": query.style_dna_version,
            "exclude_id": query.exclude_id,
        }

        return VisualRetrievalResponse(
            retrieval_version=CANONICAL_RETRIEVAL_VERSION,
            retrieval_policy_version=CANONICAL_POLICY_VERSION,
            query_provenance=query_prov,
            catalog_corpus_accounting=cat_accounting,
            historical_corpus_accounting=hist_accounting,
            catalog_matches=cat_matches,
            historical_matches=hist_matches,
        )

    def _rank_catalog_candidates(
        self,
        query: VisualRetrievalQuery,
        candidates: List[Any],
        top_k: int,
    ) -> List[CatalogVisualMatch]:
        query_vec = query.style_dna if isinstance(query.style_dna, dict) else {d.dimension_key: d.value for d in query.style_dna}
        scored: List[Tuple[float, str, str, Any, float, Any, List[str], List[str]]] = []

        for cand in candidates:
            if query.exclude_id and (query.exclude_id == cand.catalog_id or query.exclude_id == cand.sku):
                continue

            dist, score, deltas, closest, largest = compute_9d_distance_and_score(query_vec, cand.vector)
            # Secondary tie-breaker key tuple: (-score, sku, catalog_id)
            scored.append((score, cand.sku or "", cand.catalog_id, cand, dist, deltas, closest, largest))

        # Sort descending by score, ascending by SKU, ascending by catalog_id
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))

        # Filter below threshold BEFORE top-k slicing
        eligible_scored = [item for item in scored if item[0] >= self.min_proximity_pct]
        filtered_count = len(scored) - len(eligible_scored)
        if filtered_count > 0:
            logger.info("retrieval.filtered_below_threshold count=%d threshold=%.1f", filtered_count, self.min_proximity_pct)

        results: List[CatalogVisualMatch] = []
        for idx, (score, _, _, cand, _, deltas, closest, largest) in enumerate(eligible_scored[:top_k], 1):
            match = CatalogVisualMatch(
                rank=idx,
                catalog_id=cand.catalog_id,
                sku=cand.sku,
                brand=cand.brand,
                collection=cand.collection,
                product_name=cand.product_name,
                primary_image_url=cand.primary_image_url,
                visual_proximity_score=score,
                style_dimension_deltas=deltas,
                closest_dimensions=closest,
                largest_differences=largest,
                style_dna_version=CANONICAL_STYLE_DNA_VERSION,
                source_metadata_provenance=cand.source_metadata_provenance,
            )
            results.append(match)

        return results

    def _rank_historical_candidates(
        self,
        query: VisualRetrievalQuery,
        candidates: List[Any],
        top_k: int,
    ) -> List[HistoricalVisualMatch]:
        query_vec = query.style_dna if isinstance(query.style_dna, dict) else {d.dimension_key: d.value for d in query.style_dna}
        scored: List[Tuple[float, str, str, Any, float, Any, List[str], List[str]]] = []

        for cand in candidates:
            if query.exclude_id and (query.exclude_id == cand.historical_reference_id or query.exclude_id == cand.reference_key):
                continue

            dist, score, deltas, closest, largest = compute_9d_distance_and_score(query_vec, cand.vector)
            # Secondary tie-breaker key tuple: (-score, reference_key, historical_reference_id)
            scored.append((score, cand.reference_key or "", cand.historical_reference_id, cand, dist, deltas, closest, largest))

        scored.sort(key=lambda item: (-item[0], item[1], item[2]))

        # Filter below threshold BEFORE top-k slicing
        eligible_scored = [item for item in scored if item[0] >= self.min_proximity_pct]
        filtered_count = len(scored) - len(eligible_scored)
        if filtered_count > 0:
            logger.info("retrieval.filtered_below_threshold count=%d threshold=%.1f", filtered_count, self.min_proximity_pct)

        results: List[HistoricalVisualMatch] = []
        for idx, (score, _, _, cand, _, deltas, closest, largest) in enumerate(eligible_scored[:top_k], 1):
            match = HistoricalVisualMatch(
                rank=idx,
                historical_reference_id=cand.historical_reference_id,
                reference_key=cand.reference_key,
                institution=cand.institution,
                object_title=cand.object_title,
                museum_object_id=cand.museum_object_id,
                canonical_source_url=cand.canonical_source_url,
                primary_image_url=cand.primary_image_url,
                museum_metadata=cand.museum_metadata,
                visual_proximity_score=score,
                style_dimension_deltas=deltas,
                closest_dimensions=closest,
                largest_differences=largest,
                style_dna_version=CANONICAL_STYLE_DNA_VERSION,
                metadata_provenance=cand.metadata_provenance,
            )
            results.append(match)

        return results
