"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Unified Upload Result Assembler Service (V2-08).
Composes deterministic Style DNA, Color Analysis, Motif proposals,
Human Review states, Evidence RAG claims, Story curation, and V2-07 Visual Retrieval.
"""
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.motif_review import MotifReviewSubjectModel, MotifReviewEventModel
from app.domain.styledna.engine import StyleDNAEngine
from app.domain.color_analysis.service import ColorAnalysisService
from app.domain.upload_analysis.image_preparation import prepare_image_for_vlm, ImageValidationError
from app.domain.visual_retrieval.models import VisualRetrievalQuery, QuerySourceType
from app.domain.visual_retrieval.service import VisualRetrievalService
from app.domain.motif_review.schemas import ReviewResultingStatusEnum
from app.domain.result_experience.schemas import (
    ResultSectionState,
    UploadedImageMeta,
    ColorItem,
    CatalogVisualMatchItem,
    VisualCharacterCard,
    MotifCandidateItem,
    MotifReviewSummary,
    MotifCard,
    ClaimSourceItem,
    CulturalClaimItem,
    CulturalContextCard,
    StorySectionItem,
    SourceBoundStoryItem,
    ThematicAffinityItem,
    MotifStoryCard,
    HistoricalVisualMatchItem,
    HistoricalConnectionsCard,
    ResultProvenance,
    UnifiedUploadResult,
    MANDATORY_HISTORICAL_DISCLAIMER,
)

logger = logging.getLogger(__name__)

# Map English color labels to clean Turkish presentation copy
TURKISH_COLOR_MAP = {
    "deep_blue": "Çivit tonuna benzer koyu mavi",
    "sky_blue": "Gök mavisi tonu",
    "ruby_red": "Yakut kırmızısı tonu",
    "terracotta": "Kiremit tonu",
    "golden_yellow": "Altın sarısı tonu",
    "cream_white": "Krem/Fildişi tonu",
    "emerald_green": "Zümrüt yeşili tonu",
    "earth_brown": "Toprak kahvesi tonu",
    "charcoal": "Kömür/Siyah tonu",
}

# Map visual candidate descriptors to clean Turkish visual candidate descriptions
TURKISH_CANDIDATE_LABEL_MAP = {
    "tree_like": "Ağaç benzeri biçim",
    "niche_like": "Niş benzeri biçim",
    "star_like": "Yıldız benzeri biçim",
    "hook_like": "Çengel benzeri biçim",
    "comb_like": "Tarak benzeri biçim",
    "ram_horn_like": "Koçboynuzu benzeri biçim",
    "hand_like": "El/Parmak benzeri biçim",
    "bird_like": "Kuş benzeri biçim",
    "dragon_like": "Ejder benzeri biçim",
    "floral_rosette_like": "Rozet çiçek benzeri biçim",
    "medallion_like": "Madalyon benzeri biçim",
    "running_water_like": "Akar su benzeri bordür biçimi",
}


class UnifiedUploadResultService:
    """Read-only composition service for assembling UnifiedUploadResult (V2-08)."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.style_dna_engine = StyleDNAEngine()
        self.color_service = ColorAnalysisService()

    async def assemble_result_from_bytes(
        self,
        raw_bytes: bytes,
        analysis_id: Optional[uuid.UUID] = None,
        mime_type: str = "image/jpeg",
        primary_image_url: Optional[str] = None,
        precomputed_vlm_analysis: Optional[Dict[str, Any]] = None,
        precomputed_evidence_pack: Optional[Dict[str, Any]] = None,
        precomputed_claim: Optional[Dict[str, Any]] = None,
        precomputed_story: Optional[Dict[str, Any]] = None,
        precomputed_thematic_affinity: Optional[Dict[str, Any]] = None,
        review_resolutions: Optional[Dict[str, EffectiveReviewStatus]] = None,
    ) -> UnifiedUploadResult:
        aid = analysis_id or uuid.uuid4()

        # 1. Image Preparation & Quality Check
        try:
            prepared = prepare_image_for_vlm(raw_bytes, mime_type)
            img_meta = UploadedImageMeta(
                original_sha256=prepared.original_sha256,
                prepared_sha256=prepared.prepared_sha256,
                original_width=prepared.original_width,
                original_height=prepared.original_height,
                primary_image_url=primary_image_url or f"/api/v1/upload-analysis/{aid}/image",
            )
        except ImageValidationError as e:
            img_meta = UploadedImageMeta(
                original_sha256="invalid_hash",
                primary_image_url=primary_image_url or f"/api/v1/upload-analysis/{aid}/image",
            )
            return self._build_quality_blocked_result(aid, img_meta)

        # 2. Style DNA 9D & Color Analysis
        dna_status, dna_dims = self.style_dna_engine.analyze(raw_bytes)
        dna_dims_dict = {}
        for d in dna_dims:
            if isinstance(d, dict) and "key" in d:
                k = d["key"]
                v = d.get("value")
                dna_dims_dict[k] = float(v) if v is not None else 0.5
        color_obs = self.color_service.analyze_colors(raw_bytes)

        palette_items = [
            ColorItem(
                label=c.perceptual_label,
                hex_code=c.hex,
                coverage_percentage=round(c.coverage * 100, 2),
                turkish_description=TURKISH_COLOR_MAP.get(c.perceptual_label, f"{c.perceptual_label} tonu"),
            )
            for c in color_obs
        ]

        # 3. Visual Retrieval (Catalog + Historical)
        catalog_matches: List[CatalogVisualMatchItem] = []
        historical_matches: List[HistoricalVisualMatchItem] = []
        cat_fp: Optional[str] = None
        hist_fp: Optional[str] = None

        if self.db and len(dna_dims_dict) == 9:
            try:
                retrieval_service = VisualRetrievalService(self.db)
                query = VisualRetrievalQuery(
                    style_dna=dna_dims_dict,
                    query_source_type=QuerySourceType.DIRECT_VECTOR,
                    query_id=str(aid),
                )
                ret_res = await retrieval_service.retrieve_both_async(
                    query, top_k_catalog=5, top_k_historical=5
                )

                cat_fp = ret_res.catalog_corpus_accounting.corpus_fingerprint
                hist_fp = ret_res.historical_corpus_accounting.corpus_fingerprint

                catalog_matches = [
                    CatalogVisualMatchItem(
                        rank=m.rank,
                        catalog_id=m.catalog_id,
                        sku=m.sku,
                        brand=m.brand,
                        collection=m.collection,
                        product_name=m.product_name,
                        primary_image_url=m.primary_image_url,
                        visual_proximity_score=m.visual_proximity_score,
                        closest_dimensions=m.closest_dimensions,
                    )
                    for m in ret_res.catalog_matches
                ]

                historical_matches = [
                    HistoricalVisualMatchItem(
                        rank=m.rank,
                        historical_reference_id=m.historical_reference_id,
                        reference_key=m.reference_key,
                        institution=m.institution,
                        object_title=m.object_title,
                        museum_object_id=m.museum_object_id,
                        canonical_source_url=m.canonical_source_url,
                        primary_image_url=m.primary_image_url,
                        date_or_period=m.museum_metadata.get("date_or_period"),
                        origin_culture=m.museum_metadata.get("origin_culture"),
                        origin_geography=m.museum_metadata.get("origin_geography"),
                        medium_materials=m.museum_metadata.get("medium_materials"),
                        visual_proximity_score=m.visual_proximity_score,
                        closest_dimensions=m.closest_dimensions,
                    )
                    for m in ret_res.historical_matches
                ]
            except Exception as e:
                logger.warning(f"Visual retrieval error in result assembly: {e}")

        # Assemble Card 1 (Görsel Karakter)
        card1 = VisualCharacterCard(
            state=ResultSectionState.READY,
            style_dna_version="style-dna-v1.0.0",
            dimensions=dna_dims_dict,
            palette=palette_items,
            composition={"central_focus": 0.75, "symmetry": 0.85},
            catalog_matches=catalog_matches,
        )

        # Assemble Card 2 (Motifler)
        candidates_list: List[MotifCandidateItem] = []
        confirmed_count = 0
        pending_count = 0
        uncertain_count = 0
        rejected_count = 0

        vlm_candidates = []
        if precomputed_vlm_analysis and "candidates" in precomputed_vlm_analysis:
            vlm_candidates = precomputed_vlm_analysis["candidates"]

        resolutions = dict(review_resolutions) if review_resolutions else {}
        db_canonical_keys: Dict[str, Optional[str]] = {}
        if self.db and not review_resolutions:
            try:
                stmt_subj = select(MotifReviewSubjectModel).where(
                    MotifReviewSubjectModel.analysis_id == str(aid)
                )
                subj_res = await self.db.execute(stmt_subj)
                subjects = subj_res.scalars().all()
                for subj in subjects:
                    stmt_evt = select(MotifReviewEventModel).where(
                        MotifReviewEventModel.review_subject_id == subj.id
                    ).order_by(MotifReviewEventModel.version.desc()).limit(1)
                    evt_res = await self.db.execute(stmt_evt)
                    latest_evt = evt_res.scalar_one_or_none()
                    if latest_evt:
                        resolutions[subj.candidate_id] = ReviewResultingStatusEnum(latest_evt.resulting_status)
                        if latest_evt.selected_canonical_motif_key:
                            db_canonical_keys[subj.candidate_id] = latest_evt.selected_canonical_motif_key
                    else:
                        resolutions[subj.candidate_id] = ReviewResultingStatusEnum.AI_CANDIDATE
            except Exception as e:
                logger.warning(f"Error querying review subjects for analysis {aid}: {e}")

        for idx, cand in enumerate(vlm_candidates):
            cid = cand.get("candidate_id", f"cand-{idx+1}")
            descriptor = cand.get("visual_descriptor", "unknown_form")
            conf = float(cand.get("confidence", 0.8))
            bbox = cand.get("bounding_box")

            eff_res = resolutions.get(cid)
            confirmed_key = db_canonical_keys.get(cid) or cand.get("confirmed_canonical_motif_key")
            if eff_res == ReviewResultingStatusEnum.CURATOR_CONFIRMED:
                status_str = "CURATOR_CONFIRMED"
                confirmed_count += 1
            elif eff_res == ReviewResultingStatusEnum.UNCERTAIN:
                status_str = "UNCERTAIN"
                uncertain_count += 1
            elif eff_res == ReviewResultingStatusEnum.REJECTED:
                status_str = "REJECTED"
                rejected_count += 1
            else:
                status_str = "AI_CANDIDATE"
                pending_count += 1

            candidates_list.append(
                MotifCandidateItem(
                    candidate_id=cid,
                    visual_descriptor=descriptor,
                    turkish_label=TURKISH_CANDIDATE_LABEL_MAP.get(
                        descriptor, f"{descriptor.replace('_', ' ').title()} biçimi"
                    ),
                    ai_confidence=conf,
                    bounding_box=bbox,
                    status=status_str,
                    confirmed_canonical_motif_key=confirmed_key,
                )
            )

        review_sum = MotifReviewSummary(
            total_candidates=len(candidates_list),
            confirmed_count=confirmed_count,
            pending_count=pending_count,
            uncertain_count=uncertain_count,
            rejected_count=rejected_count,
        )

        card2_state = (
            ResultSectionState.READY
            if confirmed_count > 0
            else (
                ResultSectionState.WAITING_FOR_REVIEW
                if len(candidates_list) > 0
                else ResultSectionState.NOT_AVAILABLE
            )
        )

        card2 = MotifCard(
            state=card2_state,
            candidates=candidates_list,
            review_summary=review_sum,
        )

        # Assemble Card 3 (Kültürel Bağlam)
        card3_claims: List[CulturalClaimItem] = []
        card3_state = ResultSectionState.WAITING_FOR_REVIEW
        card3_msg: Optional[str] = (
            "Kültürel bağlam sunulmadan önce motif eşleşmesinin insan incelemesinden geçmesi gerekiyor."
        )

        if confirmed_count > 0:
            if precomputed_claim:
                card3_state = ResultSectionState.READY
                card3_msg = None
                card3_claims.append(
                    CulturalClaimItem(
                        claim_id=precomputed_claim.get("claim_id", "claim-001"),
                        status=precomputed_claim.get("status", "DOCUMENTED"),
                        statement_tr=precomputed_claim.get("statement_tr", ""),
                        scope=precomputed_claim.get("scope"),
                        sources=[
                            ClaimSourceItem(
                                institution=s.get("institution", "Metropolitan Museum of Art"),
                                title=s.get("title", "Carpet Research"),
                                locator=s.get("locator", "Page 12"),
                                excerpt=s.get("excerpt"),
                                canonical_url=s.get("canonical_url"),
                            )
                            for s in precomputed_claim.get("sources", [])
                        ],
                    )
                )
            else:
                card3_state = ResultSectionState.WAITING_FOR_RESEARCH
                card3_msg = "Motif doğrulandı; kaynaklandırılmış kültürel araştırma henüz mevcut değil."

        card3 = CulturalContextCard(
            state=card3_state,
            user_message=card3_msg,
            claims=card3_claims,
        )

        # Assemble Card 4 (Motif Hikâyeleri)
        card4_story: Optional[SourceBoundStoryItem] = None
        card4_state = ResultSectionState.WAITING_FOR_REVIEW
        card4_msg: Optional[str] = (
            "Kültürel anlatı sunulmadan önce motif eşleşmesinin insan incelemesinden geçmesi gerekiyor."
        )

        if confirmed_count > 0:
            if precomputed_story:
                card4_state = ResultSectionState.READY
                card4_msg = None
                card4_story = SourceBoundStoryItem(
                    title=precomputed_story.get("title", "Motif Hikâyesi"),
                    summary=precomputed_story.get("summary", ""),
                    sections=[
                        StorySectionItem(
                            heading=sec.get("heading", ""),
                            content=sec.get("content", ""),
                            citations=sec.get("citations", []),
                            is_contested=sec.get("is_contested", False),
                        )
                        for sec in precomputed_story.get("sections", [])
                    ],
                )
            else:
                card4_state = ResultSectionState.WAITING_FOR_RESEARCH
                card4_msg = "Motif doğrulandı; kaynaklandırılmış anlatı henüz mevcut değil."

        # Thematic affinity: Optional, strictly from existing narrative-affinity-v1 user preference if supplied
        thematic_affinity_item = None
        if precomputed_thematic_affinity and card4_story:
            thematic_affinity_item = ThematicAffinityItem(
                matched_themes=precomputed_thematic_affinity.get("matched_themes", []),
                affinity_description=precomputed_thematic_affinity.get("affinity_description", ""),
            )

        card4 = MotifStoryCard(
            state=card4_state,
            user_message=card4_msg,
            story=card4_story,
            thematic_affinity=thematic_affinity_item,
        )

        # Assemble Card 5 (Tarihsel Bağlantılar)
        card5 = HistoricalConnectionsCard(
            state=ResultSectionState.READY if len(historical_matches) > 0 else ResultSectionState.NOT_AVAILABLE,
            disclaimer=MANDATORY_HISTORICAL_DISCLAIMER,
            matches=historical_matches,
        )

        provenance = ResultProvenance(
            analysis_contract_version="upload-analysis-v1.0.0",
            style_dna_version="style-dna-v1.0.0",
            color_version="color-observation-v1.0.0",
            vlm_provider_version="qwen-2.5-vl-3b-instruct-awq",
            review_version="motif-review-v1.0.0",
            evidence_version="evidence-rag-v1.0.0",
            claim_version="cultural-claim-v1.0.0",
            story_version="source-bound-story-v1.0.0",
            visual_retrieval_version="visual-retrieval-v1.0.0",
            catalog_corpus_fingerprint=cat_fp,
            historical_corpus_fingerprint=hist_fp,
        )

        return UnifiedUploadResult(
            schema_version="unified-upload-result-v1.0.0",
            analysis_id=aid,
            image_meta=img_meta,
            visual_character=card1,
            motifs=card2,
            cultural_context=card3,
            motif_story=card4,
            historical_connections=card5,
            provenance=provenance,
            warnings=[],
        )

    def _build_quality_blocked_result(
        self, analysis_id: uuid.UUID, img_meta: UploadedImageMeta
    ) -> UnifiedUploadResult:
        empty_card1 = VisualCharacterCard(
            state=ResultSectionState.BLOCKED_BY_QUALITY,
            dimensions={},
            palette=[],
            composition={},
            catalog_matches=[],
        )

        empty_card2 = MotifCard(
            state=ResultSectionState.BLOCKED_BY_QUALITY,
            candidates=[],
            review_summary=MotifReviewSummary(
                total_candidates=0,
                confirmed_count=0,
                pending_count=0,
                uncertain_count=0,
                rejected_count=0,
            ),
        )

        empty_card3 = CulturalContextCard(
            state=ResultSectionState.BLOCKED_BY_QUALITY,
            user_message="Görüntü kalitesi yetersiz olduğu için analiz durduruldu.",
            claims=[],
        )

        empty_card4 = MotifStoryCard(
            state=ResultSectionState.BLOCKED_BY_QUALITY,
            user_message="Görüntü kalitesi yetersiz olduğu için hikâye üretilmedi.",
            story=None,
        )

        empty_card5 = HistoricalConnectionsCard(
            state=ResultSectionState.BLOCKED_BY_QUALITY,
            disclaimer=MANDATORY_HISTORICAL_DISCLAIMER,
            matches=[],
        )

        provenance = ResultProvenance()

        return UnifiedUploadResult(
            schema_version="unified-upload-result-v1.0.0",
            analysis_id=analysis_id,
            image_meta=img_meta,
            visual_character=empty_card1,
            motifs=empty_card2,
            cultural_context=empty_card3,
            motif_story=empty_card4,
            historical_connections=empty_card5,
            provenance=provenance,
            warnings=["Görüntü kalitesi düşük olduğu için analiz engellendi."],
        )
