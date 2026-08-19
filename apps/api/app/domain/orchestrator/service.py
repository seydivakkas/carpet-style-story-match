"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

UnifiedAnalysisOrchestrator Service (Phase 3 & Phase 4).
Orchestrates end-to-end pipeline:
Image Storage -> Style DNA -> Color -> VLM -> Visual Retrieval -> Cultural Claims -> Persisted Result.
"""
import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models.upload_analysis import UploadAnalysisModel, UploadAnalysisStatusEnum
from app.db.models.motif_knowledge import MotifModel, MotifStoryClaimModel
from app.domain.images.storage import LocalImageStorage
from app.domain.styledna.engine import StyleDNAEngine
from app.domain.color_analysis.service import ColorAnalysisService
from app.domain.upload_analysis.image_preparation import prepare_image_for_vlm, ImageValidationError
from app.domain.upload_analysis.service import get_vlm_provider
from app.domain.upload_analysis.vlm_provider import VLMProviderError
from app.domain.visual_retrieval.models import VisualRetrievalQuery, QuerySourceType
from app.domain.visual_retrieval.service import VisualRetrievalService
from app.domain.motif_knowledge.service import MotifKnowledgeService
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
    "palmette_like": "Palmet benzeri biçim",
    "human_figure_like_geometric": "Geometrik insan figürü benzeri biçim",
}


class UnifiedAnalysisOrchestrator:
    """Orchestrates end-to-end 5-card analysis run and DB persistence."""

    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        self.storage = LocalImageStorage()
        self.style_engine = StyleDNAEngine()
        self.color_service = ColorAnalysisService()

    async def run_analysis(
        self,
        raw_bytes: bytes,
        mime_type: str = "image/jpeg",
        analysis_id: Optional[uuid.UUID] = None
    ) -> UnifiedUploadResult:
        aid = analysis_id or uuid.uuid4()

        # 1. Image Preparation & Persistence
        try:
            prepared = prepare_image_for_vlm(raw_bytes, mime_type)
            storage_key = self.storage.save_image(aid, aid, raw_bytes, "jpg")
            img_meta = UploadedImageMeta(
                original_sha256=prepared.original_sha256,
                prepared_sha256=prepared.prepared_sha256,
                original_width=prepared.original_width,
                original_height=prepared.original_height,
                primary_image_url=f"/api/v1/upload-analysis/{aid}/image",
            )
        except ImageValidationError as e:
            img_meta = UploadedImageMeta(
                original_sha256="invalid_hash",
                primary_image_url=f"/api/v1/upload-analysis/{aid}/image",
            )
            return self._build_quality_blocked_result(aid, img_meta)

        # 2. Create DB Record (PROCESSING)
        analysis_record = UploadAnalysisModel(
            id=aid,
            original_sha256=prepared.original_sha256,
            prepared_sha256=prepared.prepared_sha256,
            image_path=storage_key,
            mime_type=mime_type,
            quality_status="PASS",
            status=UploadAnalysisStatusEnum.PROCESSING
        )
        self.db.add(analysis_record)
        await self.db.commit()

        # 3. 9D Style DNA Engine & Color Analysis
        dna_status, dna_dims = self.style_engine.analyze(raw_bytes)
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

        # 4. Real VLM Provider Inference
        vlm_candidates_raw: List[Dict[str, Any]] = []
        vlm_warnings: List[str] = []
        provider_type_str = self.settings.MOTIF_VLM_PROVIDER.upper()

        vlm_provider = get_vlm_provider(self.settings)
        if vlm_provider and provider_type_str != "DISABLED":
            try:
                analysis_out = await vlm_provider.analyze(prepared)
                for mc in analysis_out.motif_candidates:
                    vlm_candidates_raw.append({
                        "candidate_id": mc.candidate_id,
                        "visual_descriptor": mc.visual_candidate_key,
                        "proposed_canonical_motif_key": mc.proposed_canonical_motif_key,
                        "confidence": mc.confidence,
                        "bounding_box": [
                            mc.region.bounding_box.x_min,
                            mc.region.bounding_box.y_min,
                            mc.region.bounding_box.x_max,
                            mc.region.bounding_box.y_max
                        ] if mc.region and mc.region.bounding_box else None
                    })
                provider_type_str = analysis_out.provenance.provider_type
            except VLMProviderError as e:
                logger.warning(f"VLM Provider error during orchestration: {e}")
                vlm_warnings.append(f"MOTIF_ANALYSIS_UNAVAILABLE: {e}")
            except Exception as e:
                logger.warning(f"Unexpected VLM error: {e}")
                vlm_warnings.append(f"MOTIF_ANALYSIS_UNAVAILABLE: {type(e).__name__}")
        else:
            vlm_warnings.append("MOTIF_ANALYSIS_UNAVAILABLE: VLM provider is disabled in configuration.")

        # 5. Visual Retrieval (Catalog + Historical)
        catalog_matches: List[CatalogVisualMatchItem] = []
        historical_matches: List[HistoricalVisualMatchItem] = []
        cat_fp: Optional[str] = None
        hist_fp: Optional[str] = None

        if len(dna_dims_dict) == 9:
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
                logger.warning(f"Visual retrieval error in orchestrator: {e}")

        # Derive composition dynamically from real Style DNA 9D dimensions as proxy:
        # central_focus <- D8 (focal_strength), symmetry <- D6 (structural_order).
        # Note: focal_strength and structural_order act as real-valued visual proxies for central_focus and symmetry.
        comp_dict: Dict[str, Any] = {}
        if "focal_strength" in dna_dims_dict:
            comp_dict["central_focus"] = dna_dims_dict["focal_strength"]
        if "structural_order" in dna_dims_dict:
            comp_dict["symmetry"] = dna_dims_dict["structural_order"]

        # Assemble Card 1 (Görsel Karakter)
        card1 = VisualCharacterCard(
            state=ResultSectionState.READY,
            style_dna_version="style-dna-v1.0.0",
            dimensions=dna_dims_dict,
            palette=palette_items,
            composition=comp_dict,
            catalog_matches=catalog_matches,
        )

        # Assemble Card 2 (Motifler)
        candidates_list: List[MotifCandidateItem] = []
        confirmed_count = 0
        pending_count = 0
        uncertain_count = 0
        rejected_count = 0

        high_confidence_motifs: List[str] = []

        for idx, cand in enumerate(vlm_candidates_raw):
            cid = cand.get("candidate_id", f"cand-{idx+1}")
            descriptor = cand.get("visual_descriptor", "unknown_form")
            conf = float(cand.get("confidence", 0.8))
            bbox = cand.get("bounding_box")
            proposed_canon = cand.get("proposed_canonical_motif_key")

            # High confidence threshold (>= 0.85) auto-confirm rule for knowledge lookup
            if conf >= 0.85:
                status_str = "AUTO_CONFIRMED"
                confirmed_count += 1
                if proposed_canon:
                    high_confidence_motifs.append(proposed_canon)
                elif descriptor:
                    high_confidence_motifs.append(descriptor)
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
                    confirmed_canonical_motif_key=proposed_canon,
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

        # Assemble Card 3 (Kültürel Bağlam) & Card 4 (Motif Hikâyeleri) via Knowledge DB
        card3_claims: List[CulturalClaimItem] = []
        card3_state = ResultSectionState.WAITING_FOR_REVIEW
        card3_msg: Optional[str] = "Kültürel bağlam sunulmadan önce motif eşleşmesinin insan incelemesinden geçmesi gerekiyor."

        card4_story: Optional[SourceBoundStoryItem] = None
        card4_state = ResultSectionState.WAITING_FOR_REVIEW
        card4_msg: Optional[str] = "Kültürel anlatı sunulmadan önce motif eşleşmesinin insan incelemesinden geçmesi gerekiyor."

        if high_confidence_motifs:
            try:
                knowledge_service = MotifKnowledgeService(self.db)
                for motif_key in high_confidence_motifs:
                    claims_res = await knowledge_service.list_claims(motif_id_or_key=motif_key)
                    if claims_res.claims:
                        card3_state = ResultSectionState.READY
                        card3_msg = None
                        for c in claims_res.claims:
                            card3_claims.append(
                                CulturalClaimItem(
                                    claim_id=str(c.id),
                                    status=c.status.value if hasattr(c.status, "value") else str(c.status),
                                    statement_tr=c.claim_text_tr,
                                    scope="Müzebilimsel Hakikat Matrisi",
                                    sources=[
                                        ClaimSourceItem(
                                            institution=cs.source.institution_name,
                                            title=cs.source.title,
                                            locator=cs.locator or "",
                                            excerpt=cs.source_note,
                                            canonical_url=cs.source.canonical_url
                                        )
                                        for cs in c.sources
                                    ]
                                )
                            )

                        # Build Card 4 Story from DB claims
                        if not card4_story and claims_res.claims:
                            first_claim = claims_res.claims[0]
                            card4_state = ResultSectionState.READY
                            card4_msg = None
                            card4_story = SourceBoundStoryItem(
                                title=f"{motif_key.title()} Motifinin Anlatısal ve Kültürel Kökleri",
                                summary=first_claim.claim_text_tr,
                                sections=[
                                    StorySectionItem(
                                        heading="Geleneksel Kökler ve Sembolizm",
                                        content=first_claim.claim_text_tr,
                                        citations=[s.source.title for s in first_claim.sources],
                                        is_contested=bool(first_claim.contest_note)
                                    )
                                ]
                            )
            except Exception as e:
                logger.warning(f"Motif knowledge lookup failed in orchestrator: {e}")

        card3 = CulturalContextCard(
            state=card3_state,
            user_message=card3_msg,
            claims=card3_claims,
        )

        card4 = MotifStoryCard(
            state=card4_state,
            user_message=card4_msg,
            story=card4_story,
            thematic_affinity=None,
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
            vlm_provider_version=provider_type_str,
            review_version="motif-review-v1.0.0",
            evidence_version="evidence-rag-v1.0.0",
            claim_version="cultural-claim-v1.0.0",
            story_version="source-bound-story-v1.0.0",
            visual_retrieval_version="visual-retrieval-v1.0.0",
            catalog_corpus_fingerprint=cat_fp,
            historical_corpus_fingerprint=hist_fp,
        )

        unified_res = UnifiedUploadResult(
            schema_version="unified-upload-result-v1.0.0",
            analysis_id=aid,
            image_meta=img_meta,
            visual_character=card1,
            motifs=card2,
            cultural_context=card3,
            motif_story=card4,
            historical_connections=card5,
            provenance=provenance,
            warnings=vlm_warnings,
        )

        # 6. Update DB Record to COMPLETED with persisted snapshot
        analysis_record.status = UploadAnalysisStatusEnum.COMPLETED
        analysis_record.style_dna_result = dna_dims_dict
        analysis_record.color_result = [c.model_dump() for c in palette_items]
        analysis_record.vlm_result = vlm_candidates_raw
        analysis_record.unified_result = unified_res.model_dump(mode="json")
        await self.db.commit()

        return unified_res

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


class CarpetAnalysisOrchestrator:
    """Legacy RAG / CLI research pipeline orchestrator."""

    def __init__(self, vlm_provider=None):
        self.vlm_provider = vlm_provider
        self.style_engine = StyleDNAEngine()
        self.color_service = ColorAnalysisService()

    async def run_pipeline(
        self,
        raw_bytes: bytes,
        mime_type: str = "image/jpeg",
        stages: Optional[List[str]] = None,
        verified_subject_motif: Optional[str] = None
    ) -> Dict[str, Any]:
        from app.domain.research import SourceResearchService, resolve_canonical_motif_subject

        stages = stages or ["visual"]
        results = {}

        if "visual" in stages:
            dna_status, dna_dims = self.style_engine.analyze(raw_bytes)
            colors = self.color_service.analyze_colors(raw_bytes)
            results["visual"] = {
                "style_dna": dna_dims,
                "colors": [c.model_dump() for c in colors]
            }

        if "research" in stages and verified_subject_motif:
            research_service = SourceResearchService()
            subject = resolve_canonical_motif_subject(verified_subject_motif)
            pack = await research_service.execute_research(subject)
            results["evidence_pack"] = pack.model_dump()

        return results


