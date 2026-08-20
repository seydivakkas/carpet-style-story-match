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
from app.domain.motif_knowledge.service import MotifKnowledgeService
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
                if conf >= 0.85:
                    status_str = "AUTO_CONFIRMED"
                    confirmed_count += 1
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

        # Assemble Card 3 (Kültürel Bağlam) & Card 4 (Motif Hikâyeleri)
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

        # 1. Check precomputed first
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
                            institution=s.get("institution", "Müze Kaynağı"),
                            title=s.get("title", "Carpet Research"),
                            locator=s.get("locator", ""),
                            excerpt=s.get("excerpt"),
                            canonical_url=s.get("canonical_url"),
                        )
                        for s in precomputed_claim.get("sources", [])
                    ],
                )
            )

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

        # 2. If claims or stories are not precomputed, look up from DB
        motifs_to_lookup = []
        for c in candidates_list:
            if c.confirmed_canonical_motif_key:
                motifs_to_lookup.append(c.confirmed_canonical_motif_key)
            elif c.visual_descriptor:
                motifs_to_lookup.append(c.visual_descriptor)

        if self.db and motifs_to_lookup and (not card3_claims or not card4_story):
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

                        norm_k = motif_key.replace('_', '-')
                        if norm_k in THEMATIC_AFFINITY_MAP:
                            themes, aff_desc = THEMATIC_AFFINITY_MAP[norm_k]
                            for t in themes:
                                if t not in all_matched_themes:
                                    all_matched_themes.append(t)
                            affinity_descriptions.append(aff_desc)

                if story_sections and not card4_story:
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
                logger.warning(f"Motif knowledge lookup failed in result assembler: {e}", exc_info=True)

        if precomputed_thematic_affinity and not thematic_affinity_item:
            thematic_affinity_item = ThematicAffinityItem(
                matched_themes=precomputed_thematic_affinity.get("matched_themes", []),
                affinity_description=precomputed_thematic_affinity.get("affinity_description", ""),
            )

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

    async def refresh_unified_result_with_reviews(
        self,
        analysis_id: uuid.UUID,
        current_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Dynamically applies latest human curator review decisions from motif_review_events
        to an existing unified result dictionary, updating motif candidates, cultural claims,
        stories, and thematic affinity.
        """
        if not self.db or not current_dict:
            return current_dict

        try:
            aid_str = str(analysis_id)
            aid_hex = analysis_id.hex if hasattr(analysis_id, "hex") else aid_str.replace("-", "")
            stmt_subj = select(MotifReviewSubjectModel).where(
                (MotifReviewSubjectModel.analysis_id == aid_str) |
                (MotifReviewSubjectModel.analysis_id == aid_hex)
            )
            subj_res = await self.db.execute(stmt_subj)
            subjects = subj_res.scalars().all()
            if not subjects:
                return current_dict

            resolutions: Dict[str, str] = {}
            canonical_keys: Dict[str, Optional[str]] = {}

            for subj in subjects:
                stmt_evt = select(MotifReviewEventModel).where(
                    MotifReviewEventModel.review_subject_id == subj.id
                ).order_by(MotifReviewEventModel.version.desc()).limit(1)
                evt_res = await self.db.execute(stmt_evt)
                latest_evt = evt_res.scalar_one_or_none()
                if latest_evt:
                    resolutions[subj.candidate_id] = latest_evt.resulting_status
                    if latest_evt.selected_canonical_motif_key:
                        canonical_keys[subj.candidate_id] = latest_evt.selected_canonical_motif_key

            if not resolutions:
                return current_dict

            # Update candidates list in motifs
            motifs_card = current_dict.get("motifs", {})
            candidates = motifs_card.get("candidates", [])
            confirmed_count = 0
            pending_count = 0
            uncertain_count = 0
            rejected_count = 0
            confirmed_motifs: List[str] = []

            for cand in candidates:
                cid = cand.get("candidate_id")
                if cid in resolutions:
                    stat = resolutions[cid]
                    cand["status"] = stat
                    if cid in canonical_keys and canonical_keys[cid]:
                        cand["confirmed_canonical_motif_key"] = canonical_keys[cid]

                c_stat = cand.get("status")
                canon_k = cand.get("confirmed_canonical_motif_key") or cand.get("visual_descriptor")
                if c_stat in ("CURATOR_CONFIRMED", "AUTO_CONFIRMED"):
                    confirmed_count += 1
                    if canon_k:
                        confirmed_motifs.append(canon_k)
                elif c_stat == "UNCERTAIN":
                    uncertain_count += 1
                elif c_stat == "REJECTED":
                    rejected_count += 1
                else:
                    pending_count += 1

            motifs_card["review_summary"] = {
                "total_candidates": len(candidates),
                "confirmed_count": confirmed_count,
                "pending_count": pending_count,
                "uncertain_count": uncertain_count,
                "rejected_count": rejected_count
            }

            if confirmed_count > 0:
                motifs_card["state"] = "READY"
            elif len(candidates) > 0:
                motifs_card["state"] = "WAITING_FOR_REVIEW"
            else:
                motifs_card["state"] = "NOT_AVAILABLE"

            current_dict["motifs"] = motifs_card

            # If motifs confirmed, refresh Card 3 (Cultural Context) & Card 4 (Motif Stories)
            if confirmed_motifs:
                knowledge_service = MotifKnowledgeService(self.db)
                story_sections = []
                all_matched_themes = []
                affinity_descriptions = []
                card3_claims = []

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

                for motif_key in confirmed_motifs:
                    norm_keys = [motif_key, motif_key.replace('_', '-'), motif_key.replace('-', '_')]
                    claims_res = None
                    for nk in norm_keys:
                        claims_res = await knowledge_service.list_claims(motif_id_or_key=nk)
                        if claims_res and claims_res.claims:
                            break

                    if claims_res and claims_res.claims:
                        tr_name = TURKISH_MOTIF_NAMES.get(motif_key, motif_key.replace('-', ' ').title())
                        for c in claims_res.claims:
                            claim_sources = []
                            for cs in c.sources:
                                inst = getattr(cs.source, "creator_or_institution", None) or getattr(cs.source, "title", "Müze Kaynağı")
                                tit = getattr(cs.source, "title", "Akademik Kaynak")
                                loc = getattr(cs, "locator", "") or ""
                                exc = getattr(cs, "source_note", None) or getattr(cs.source, "citation_text", "")
                                curl = getattr(cs.source, "url", None)
                                claim_sources.append({
                                    "institution": inst,
                                    "title": tit,
                                    "locator": loc,
                                    "excerpt": exc,
                                    "canonical_url": curl
                                })

                            card3_claims.append({
                                "claim_id": str(c.id),
                                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                                "statement_tr": c.claim_text_tr or f"{tr_name} motifi dokuma geleneğinde belgelenmiştir.",
                                "scope": "Müzebilimsel ve Etnografik Hakikat Matrisi",
                                "sources": claim_sources
                            })

                            citations_list = [cs.source.title for cs in c.sources if hasattr(cs, "source") and hasattr(cs.source, "title")]
                            story_sections.append({
                                "heading": f"{tr_name} Motifinin Kültürel ve Sanatsal Kökleri",
                                "content": c.claim_text_tr or "",
                                "citations": citations_list,
                                "is_contested": bool(c.contest_note or (hasattr(c.status, "value") and c.status.value == "CONTESTED"))
                            })
                            if c.context_note:
                                story_sections.append({
                                    "heading": f"{tr_name} için Bölgesel ve Bağlamsal Notlar",
                                    "content": c.context_note,
                                    "citations": citations_list,
                                    "is_contested": False
                                })
                            if c.contest_note:
                                story_sections.append({
                                    "heading": f"{tr_name} Hakkındaki Akademik Tartışmalar",
                                    "content": c.contest_note,
                                    "citations": citations_list,
                                    "is_contested": True
                                })

                        norm_k = motif_key.replace('_', '-')
                        if norm_k in THEMATIC_AFFINITY_MAP:
                            themes, aff_desc = THEMATIC_AFFINITY_MAP[norm_k]
                            for t in themes:
                                if t not in all_matched_themes:
                                    all_matched_themes.append(t)
                            affinity_descriptions.append(aff_desc)

                if card3_claims:
                    current_dict["cultural_context"] = {
                        "state": "READY",
                        "user_message": None,
                        "claims": card3_claims
                    }

                if story_sections:
                    primary_motif_name = TURKISH_MOTIF_NAMES.get(confirmed_motifs[0], confirmed_motifs[0].replace('-', ' ').title())
                    current_dict["motif_story"] = {
                        "state": "READY",
                        "user_message": None,
                        "story": {
                            "title": f"{primary_motif_name} ve Dokuma Geleneğindeki Anlatısal Kökleri",
                            "summary": story_sections[0]["content"],
                            "sections": story_sections
                        },
                        "thematic_affinity": {
                            "matched_themes": all_matched_themes,
                            "affinity_description": " ".join(affinity_descriptions)
                        } if all_matched_themes else None
                    }
        except Exception as e:
            logger.warning(f"Failed to refresh unified result with reviews for {analysis_id}: {e}", exc_info=True)

        return current_dict
