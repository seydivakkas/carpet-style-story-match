"""Deterministic explanation builder for Narrative Affinity Engine v1."""
from typing import List
from app.db.models.carpet_narrative_affinity import (
    NarrativeAffinityStatusEnum,
    NarrativeAffinityLevelEnum,
    NarrativeNotAvailableReasonEnum,
    ThemeSupportStatusEnum
)
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES
from app.domain.motif_knowledge.schemas import ClaimSourceRead, CuratedSourceRead
from app.domain.narrative_affinity.engine import EngineAffinityOutput, EngineThemeSnapshot
from app.domain.narrative_affinity.schemas import (
    NarrativeAffinityExplanationRead,
    AlignedThemeExplanationRead,
    UnmatchedThemeExplanationRead,
    ContestedOverlapExplanationRead
)


class NarrativeAffinityExplanationBuilder:
    """Builds deterministic, zero-LLM explanations for narrative affinity results."""

    @classmethod
    def build_explanation(cls, engine_output: EngineAffinityOutput) -> NarrativeAffinityExplanationRead:
        overall_text = cls._build_overall_text(engine_output)

        aligned_themes: List[AlignedThemeExplanationRead] = []
        unmatched_themes: List[UnmatchedThemeExplanationRead] = []
        contested_overlaps: List[ContestedOverlapExplanationRead] = []

        # Sort snapshots for aligned themes:
        # 1. user_interest_weight DESC
        # 2. Canonical N1..N8 order
        canonical_order = {t["key"]: i for i, t in enumerate(CANONICAL_NARRATIVE_THEMES)}
        theme_names = {t["key"]: t.get("label_tr", t.get("name_tr", t["key"])) for t in CANONICAL_NARRATIVE_THEMES}

        sorted_snapshots = sorted(
            engine_output.theme_snapshots,
            key=lambda s: (-s.user_interest_weight, canonical_order.get(s.theme_key, 999))
        )

        for s in sorted_snapshots:
            t_name = theme_names.get(s.theme_key, s.theme_key)

            # 1. Aligned themes (confirmed matches)
            if s.confirmed_match:
                ctx_note = None
                app_note = None
                sources: List[ClaimSourceRead] = []

                for sa in s.story_associations:
                    claim = sa.claim
                    if not claim:
                        continue
                    if sa.applicability_note:
                        app_note = sa.applicability_note
                    if claim.context_note:
                        ctx_note = claim.context_note

                    if claim.sources:
                        for cs in claim.sources:
                            sources.append(
                                ClaimSourceRead(
                                    source=CuratedSourceRead.model_validate(cs.source),
                                    locator=cs.locator,
                                    source_note=cs.source_note
                                )
                            )

                if s.carpet_support_status == ThemeSupportStatusEnum.DOCUMENTED:
                    summary = f"'{t_name}' teması, halı üzerindeki motiflerle ilgili doğrudan kaynaklandırılmış anlatılarla desteklenmektedir."
                else:
                    summary = f"'{t_name}' teması, halı üzerindeki motiflerle ilgili bağlamsal kaynaklandırılmış anlatılarla desteklenmektedir."

                aligned_themes.append(
                    AlignedThemeExplanationRead(
                        theme_key=s.theme_key,
                        user_interest_level=s.user_interest_level,
                        carpet_support_status=s.carpet_support_status,
                        context_note=ctx_note,
                        applicability_note=app_note,
                        summary_tr=summary,
                        sources=sources
                    )
                )

            # 2. Unmatched selected themes
            elif s.user_selected and not s.confirmed_match:
                summary = f"Seçtiğiniz '{t_name}' teması için bu halıda doğrulanmış anlatı kanıtı bulunmamaktadır."
                unmatched_themes.append(
                    UnmatchedThemeExplanationRead(
                        theme_key=s.theme_key,
                        user_interest_level=s.user_interest_level,
                        carpet_support_status=s.carpet_support_status,
                        summary_tr=summary
                    )
                )

            # 3. Contested overlaps
            if s.contested_overlap:
                cnt_note = None
                app_note = None
                sources: List[ClaimSourceRead] = []

                for sa in s.story_associations:
                    claim = sa.claim
                    if not claim:
                        continue
                    if sa.applicability_note:
                        app_note = sa.applicability_note
                    if claim.contest_note:
                        cnt_note = claim.contest_note

                    if claim.sources:
                        for cs in claim.sources:
                            sources.append(
                                ClaimSourceRead(
                                    source=CuratedSourceRead.model_validate(cs.source),
                                    locator=cs.locator,
                                    source_note=cs.source_note
                                )
                            )

                summary = f"Seçtiğiniz '{t_name}' teması ile ilişkili halı anlatıları kaynaklarda tartışmalıdır."

                contested_overlaps.append(
                    ContestedOverlapExplanationRead(
                        theme_key=s.theme_key,
                        user_interest_level=s.user_interest_level,
                        contest_note=cnt_note,
                        applicability_note=app_note,
                        summary_tr=summary,
                        sources=sources
                    )
                )

        return NarrativeAffinityExplanationRead(
            overall_text_tr=overall_text,
            aligned_themes=aligned_themes,
            unmatched_themes=unmatched_themes,
            contested_overlaps=contested_overlaps
        )

    @staticmethod
    def _build_overall_text(engine_output: EngineAffinityOutput) -> str:
        if engine_output.status == NarrativeAffinityStatusEnum.NOT_AVAILABLE:
            reason = engine_output.not_available_reason
            if reason == NarrativeNotAvailableReasonEnum.USER_NARRATIVE_SKIPPED:
                return "Bu değerlendirme için kullanıcı anlatı teması seçilmedi."
            elif reason == NarrativeNotAvailableReasonEnum.NO_SELECTED_USER_THEMES:
                return "Bu değerlendirme için herhangi bir anlatı teması seçilmedi."
            elif reason == NarrativeNotAvailableReasonEnum.NO_CARPET_NARRATIVE_THEME_EVIDENCE:
                return "Bu halı için tema karşılaştırmasına yetecek kaynaklandırılmış anlatı kanıtı bulunmuyor."
            elif reason == NarrativeNotAvailableReasonEnum.ONLY_CONTESTED_CARPET_EVIDENCE:
                return "Mevcut anlatı kanıtları tartışmalı yorumlardan oluştuğu için güvenilir bir anlatı yakınlığı sınıflandırması yapılmadı."
            return "Anlatı yakınlığı hesaplanamadı."

        level = engine_output.affinity_level
        if level == NarrativeAffinityLevelEnum.VERY_STRONG:
            return "Kaynaklandırılmış halı anlatıları, seçtiğiniz temaların büyük bölümünü destekliyor."
        elif level == NarrativeAffinityLevelEnum.STRONG:
            return "Kaynaklandırılmış anlatılar, seçtiğiniz ana temaların önemli bir bölümüyle örtüşüyor."
        elif level == NarrativeAffinityLevelEnum.MODERATE:
            return "Seçtiğiniz temaların bir kısmı kaynaklandırılmış halı anlatılarıyla örtüşüyor."
        elif level == NarrativeAffinityLevelEnum.LIMITED:
            return "Mevcut kaynaklandırılmış anlatılarla seçtiğiniz temalar arasında sınırlı örtüşme bulunuyor."

        return "Anlatı yakınlığı tamamlandı."
