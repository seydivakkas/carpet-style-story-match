"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

UnifiedAnalysisOrchestrator Service (Phase 3 & Phase 4).
Orchestrates end-to-end pipeline:
Image Storage -> Style DNA -> Color -> VLM -> Visual Retrieval -> Cultural Claims -> Persisted Result.
"""
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.db.models.upload_analysis import UploadAnalysisModel, UploadAnalysisStatusEnum
from app.db.models.motif_knowledge import MotifModel, MotifStoryClaimModel
from app.db.models.motif_review import MotifReviewSubjectModel
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
    "horn_like": "Koçboynuzu benzeri biçim",
    "ram_horn_like": "Koçboynuzu benzeri biçim",
    "hand_like": "El/Parmak benzeri biçim",
    "bird_like": "Kuş benzeri biçim",
    "dragon_like": "Ejder benzeri biçim",
    "floral_rosette_like": "Rozet çiçek benzeri biçim",
    "rosette_like": "Rozet çiçek benzeri biçim",
    "medallion_like": "Madalyon benzeri biçim",
    "running_water_like": "Akar su / Kıvrımdal biçimi",
    "vine_scroll_like": "Kıvrımdal / İslimi biçimi",
    "palmette_like": "Palmet benzeri biçim",
    "lotus_like": "Lotus / Nilüfer biçimi",
    "cloud_band_like": "Bulut kümesi biçimi",
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
            blocked_res = self._build_quality_blocked_result(aid, img_meta)

            stmt = select(UploadAnalysisModel).where(UploadAnalysisModel.id == aid)
            res = await self.db.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                record = UploadAnalysisModel(
                    id=aid,
                    original_sha256="invalid_hash",
                    quality_status="FAIL",
                    status=UploadAnalysisStatusEnum.BLOCKED_BY_QUALITY,
                    unified_result=blocked_res.model_dump(mode="json")
                )
                self.db.add(record)
            else:
                record.quality_status = "FAIL"
                record.status = UploadAnalysisStatusEnum.BLOCKED_BY_QUALITY
                record.unified_result = blocked_res.model_dump(mode="json")
            await self.db.commit()
            return blocked_res

        # 2. Create DB Record (PROCESSING)
        stmt = select(UploadAnalysisModel).where(UploadAnalysisModel.id == aid)
        res = await self.db.execute(stmt)
        analysis_record = res.scalar_one_or_none()
        if not analysis_record:
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
        else:
            analysis_record.original_sha256 = prepared.original_sha256
            analysis_record.prepared_sha256 = prepared.prepared_sha256
            analysis_record.image_path = storage_key
            analysis_record.mime_type = mime_type
            analysis_record.quality_status = "PASS"
            analysis_record.status = UploadAnalysisStatusEnum.PROCESSING
        await self.db.commit()

        # 3. Parallel Execution: Style DNA (threadpool), Color Analysis (threadpool), VLM Inference (async I/O)
        provider_type_str = self.settings.MOTIF_VLM_PROVIDER.upper()
        vlm_provider = get_vlm_provider(self.settings)

        async def _run_vlm():
            if vlm_provider and provider_type_str != "DISABLED":
                return await vlm_provider.analyze(prepared)
            return None

        results = await asyncio.gather(
            run_in_threadpool(self.style_engine.analyze, raw_bytes),
            run_in_threadpool(self.color_service.analyze_colors, raw_bytes),
            _run_vlm(),
            return_exceptions=True
        )

        dna_res, color_res, vlm_res = results[0], results[1], results[2]

        # Handle Style DNA result
        if isinstance(dna_res, Exception):
            raise dna_res
        dna_status, dna_dims = dna_res
        dna_dims_dict = {}
        for d in dna_dims:
            if isinstance(d, dict) and "key" in d:
                k = d["key"]
                v = d.get("value")
                dna_dims_dict[k] = float(v) if v is not None else 0.5

        # Handle Color Analysis result
        if isinstance(color_res, Exception):
            raise color_res
        color_obs = color_res
        palette_items = [
            ColorItem(
                label=c.perceptual_label,
                hex_code=c.hex,
                coverage_percentage=round(c.coverage * 100, 2),
                turkish_description=TURKISH_COLOR_MAP.get(c.perceptual_label, f"{c.perceptual_label} tonu"),
            )
            for c in color_obs
        ]

        # Handle VLM Inference result
        vlm_candidates_raw: List[Dict[str, Any]] = []
        vlm_warnings: List[str] = []

        if isinstance(vlm_res, Exception):
            if isinstance(vlm_res, VLMProviderError):
                logger.warning(f"VLM Provider error during orchestration: {vlm_res}")
                vlm_warnings.append(f"MOTIF_ANALYSIS_UNAVAILABLE: {vlm_res}")
            else:
                logger.warning(f"Unexpected VLM error: {vlm_res}")
                vlm_warnings.append(f"MOTIF_ANALYSIS_UNAVAILABLE: {type(vlm_res).__name__}")
        elif vlm_res is not None:
            for mc in vlm_res.motif_candidates:
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
            provider_type_str = vlm_res.provenance.provider_type
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

        # Register in Review Subjects for Curator Review panel if db is available
        if self.db and vlm_candidates_raw:
            try:
                import hashlib
                for cand in vlm_candidates_raw:
                    cid = cand.get("candidate_id")
                    if not cid:
                        continue
                    stmt_ex = select(MotifReviewSubjectModel).where(
                        MotifReviewSubjectModel.analysis_id == str(aid),
                        MotifReviewSubjectModel.candidate_id == cid,
                    )
                    ex_res = await self.db.execute(stmt_ex)
                    if not ex_res.scalar_one_or_none():
                        snap_hash = hashlib.sha256(f"{aid}:{cid}:{cand.get('visual_descriptor')}".encode()).hexdigest()
                        new_subj = MotifReviewSubjectModel(
                            review_subject_id=f"rev-{str(aid)[:8]}-{cid}",
                            analysis_id=str(aid),
                            candidate_id=cid,
                            visual_candidate_key=cand.get("visual_descriptor", "unknown"),
                            proposed_canonical_motif_key=cand.get("proposed_canonical_motif_key"),
                            original_candidate_status="AI_CANDIDATE",
                            candidate_confidence=float(cand.get("confidence", 0.8)),
                            candidate_snapshot=cand,
                            snapshot_hash=snap_hash,
                            model_provenance={"provider_type": provider_type_str},
                            ontology_version="motif-ontology-v1.0.0",
                            review_version=0
                        )
                        self.db.add(new_subj)
                await self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to auto-register review subjects: {e}")

        # Assemble Card 3 (Kültürel Bağlam) & Card 4 (Motif Hikâyeleri) via Knowledge DB
        card3_claims: List[CulturalClaimItem] = []
        card3_state = ResultSectionState.WAITING_FOR_REVIEW
        card3_msg: Optional[str] = "Kültürel bağlam sunulmadan önce motif eşleşmesinin insan incelemesinden geçmesi gerekiyor."

        card4_story: Optional[SourceBoundStoryItem] = None
        card4_state = ResultSectionState.WAITING_FOR_REVIEW
        card4_msg: Optional[str] = "Kültürel anlatı sunulmadan önce motif eşleşmesinin insan incelemesinden geçmesi gerekiyor."
        thematic_affinity_item: Optional[ThematicAffinityItem] = None

        TURKISH_MOTIF_NAMES = {
            "medallion": "Madalyon",
            "tree-of-life": "Hayat Ağacı",
            "tree_of_life": "Hayat Ağacı",
            "geometric-star": "Sekiz Köşeli Yıldız",
            "geometric_star": "Sekiz Köşeli Yıldız",
            "mihrab": "Mihrap (Niş)",
            "palmette": "Palmet",
            "lotus": "Lotus (Nilüfer)",
            "cloud-band": "Çin Bulutu (Bulut Kancası)",
            "cloud_band": "Çin Bulutu (Bulut Kancası)",
            "scrolling-vine": "Kıvrımdal (İslimi)",
            "scrolling_vine": "Kıvrımdal (İslimi)",
            "elibelinde": "Elibelinde",
            "ram-horn": "Koçboynuzu",
            "ram_horn": "Koçboynuzu",
            "comb": "Tarak",
            "mystery-hook": "Çengel",
        }

        THEMATIC_AFFINITY_MAP = {
            "tree-of-life": (["Doğa & Büyüme", "Süreklilik & Bağ", "Kültürel Miras"], "Hayat ağacı motifi, nesiller arası bağ, soy sürekliliği ve köklenme temasını görselleştirir."),
            "medallion": (["Denge & Düzen", "Gelenek & Zanaat", "Kültürel Miras"], "Merkezi madalyon mimarisi, simetri hiyerarşisi ve klasik saray dokuma düzenini temsil eder."),
            "geometric-star": (["Denge & Düzen", "Kültürel Miras", "Gelenek & Zanaat"], "Sekiz köşeli geometrik yıldız, erken dönem modüler alan düzeni ve kozmolojik dengeyi yansıtır."),
            "mihrab": (["Aidiyet & Yuva", "Denge & Düzen", "Gelenek & Zanaat"], "Mihrap niş formu, mekânsal aidiyet ve mimari yönelim odağını simgeler."),
            "palmette": (["Doğa & Büyüme", "Yenilenme & Dönüşüm", "Gelenek & Zanaat"], "Palmet ve lotus yaprakları, stilize bitkisel akış ve doğadaki organik ritmi ifade eder."),
            "lotus": (["Doğa & Büyüme", "Yenilenme & Dönüşüm"], "Lotus motifi, klasik Doğu sanatında yenilenme ve stilize çiçek zarafetini taşır."),
            "scrolling-vine": (["Doğa & Büyüme", "Süreklilik & Bağ", "Denge & Düzen"], "Kıvrımdal hatları, sonsuz devam eden organik ritim ve görsel akıcılık sağlar."),
            "elibelinde": (["Aidiyet & Yuva", "Süreklilik & Bağ", "Gelenek & Zanaat"], "Elibelinde figürü, Anadolu dokuma geleneğinde analık, bereket ve yuva koruyuculuğunu simgeler."),
            "ram-horn": (["Gelenek & Zanaat", "Kültürel Miras"], "Koçboynuzu motifi, geleneksel el sanatlarında güç, bereket ve stilize geometrik formu temsil eder."),
            "comb": (["Gelenek & Zanaat", "Aidiyet & Yuva"], "Tarak motifi, dokuma zanaatının aracı ve arınma sembolizmi bağlamında yer alır."),
        }

        # Query knowledge claims for any candidate with a proposed canonical motif key
        motifs_to_lookup = list(high_confidence_motifs)
        if not motifs_to_lookup:
            for c in candidates_list:
                if c.confirmed_canonical_motif_key:
                    motifs_to_lookup.append(c.confirmed_canonical_motif_key)
                elif c.visual_descriptor:
                    motifs_to_lookup.append(c.visual_descriptor)

        if motifs_to_lookup:
            try:
                knowledge_service = MotifKnowledgeService(self.db)
                story_sections: List[StorySectionItem] = []
                all_matched_themes: List[str] = []
                affinity_descriptions: List[str] = []

                for motif_key in motifs_to_lookup:
                    norm_keys = [motif_key, motif_key.replace('_', '-'), motif_key.replace('-', '_')]
                    claims_res = None
                    for nk in norm_keys:
                        claims_res = await knowledge_service.list_claims(motif_id_or_key=nk)
                        if claims_res and claims_res.claims:
                            break

                    if claims_res and claims_res.claims:
                        card3_state = ResultSectionState.READY
                        card3_msg = None
                        tr_name = TURKISH_MOTIF_NAMES.get(motif_key, motif_key.replace('-', ' ').title())

                        for c in claims_res.claims:
                            claim_sources: List[ClaimSourceItem] = []
                            for cs in c.sources:
                                inst = getattr(cs.source, "creator_or_institution", None) or getattr(cs.source, "title", "Müze Kaynağı")
                                tit = getattr(cs.source, "title", "Akademik Kaynak")
                                loc = getattr(cs, "locator", "") or ""
                                exc = getattr(cs, "source_note", None) or getattr(cs.source, "citation_text", "")
                                curl = getattr(cs.source, "url", None)
                                claim_sources.append(
                                    ClaimSourceItem(
                                        institution=inst,
                                        title=tit,
                                        locator=loc,
                                        excerpt=exc,
                                        canonical_url=curl
                                    )
                                )

                            card3_claims.append(
                                CulturalClaimItem(
                                    claim_id=str(c.id),
                                    status=c.status.value if hasattr(c.status, "value") else str(c.status),
                                    statement_tr=c.claim_text_tr or f"{tr_name} motifi dokuma geleneğinde belgelenmiştir.",
                                    scope="Müzebilimsel ve Etnografik Hakikat Matrisi",
                                    sources=claim_sources
                                )
                            )

                            # Build Story Sections
                            citations_list = [cs.source.title for cs in c.sources if hasattr(cs, "source") and hasattr(cs.source, "title")]
                            story_sections.append(
                                StorySectionItem(
                                    heading=f"{tr_name} Motifinin Kültürel ve Sanatsal Kökleri",
                                    content=c.claim_text_tr or "",
                                    citations=citations_list,
                                    is_contested=bool(c.contest_note or (hasattr(c.status, "value") and c.status.value == "CONTESTED"))
                                )
                            )
                            if c.context_note:
                                story_sections.append(
                                    StorySectionItem(
                                        heading=f"{tr_name} için Bölgesel ve Bağlamsal Notlar",
                                        content=c.context_note,
                                        citations=citations_list,
                                        is_contested=False
                                    )
                                )
                            if c.contest_note:
                                story_sections.append(
                                    StorySectionItem(
                                        heading=f"{tr_name} Hakkındaki Akademik Tartışmalar",
                                        content=c.contest_note,
                                        citations=citations_list,
                                        is_contested=True
                                    )
                                )

                        # Match Thematic Affinity
                        norm_k = motif_key.replace('_', '-')
                        if norm_k in THEMATIC_AFFINITY_MAP:
                            themes, aff_desc = THEMATIC_AFFINITY_MAP[norm_k]
                            for t in themes:
                                if t not in all_matched_themes:
                                    all_matched_themes.append(t)
                            affinity_descriptions.append(aff_desc)

                if story_sections:
                    card4_state = ResultSectionState.READY
                    card4_msg = None
                    primary_motif_name = TURKISH_MOTIF_NAMES.get(motifs_to_lookup[0], motifs_to_lookup[0].replace('-', ' ').title())
                    card4_story = SourceBoundStoryItem(
                        title=f"{primary_motif_name} ve Dokuma Geleneğindeki Anlatısal Kökleri",
                        summary=story_sections[0].content,
                        sections=story_sections
                    )

                if all_matched_themes:
                    thematic_affinity_item = ThematicAffinityItem(
                        matched_themes=all_matched_themes,
                        affinity_description=" ".join(affinity_descriptions)
                    )

            except Exception as e:
                logger.warning(f"Motif knowledge lookup failed in orchestrator: {e}", exc_info=True)

        card3 = CulturalContextCard(
            state=card3_state,
            user_message=card3_msg,
            claims=card3_claims,
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


