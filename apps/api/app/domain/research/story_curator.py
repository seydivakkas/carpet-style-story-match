"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-05 Source-Bound Story Curator Implementation.
Renders Turkish presentation prose strictly bound to validated cultural claims.
Default mode TEMPLATE_ONLY operates 100% offline with zero external network or model requirements.
"""
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.domain.research.models import EvidencePack
from app.domain.research.claim_models import ValidatedCulturalClaim, CulturalClaimStatus
from app.domain.research.story_models import (
    StoryPresentation,
    StorySection,
    StoryCitation,
    SOURCE_BOUND_STORY_SCHEMA_VERSION
)


class StoryCuratorProvider(ABC):
    """Abstract interface for source-bound story curation providers."""

    @abstractmethod
    def generate_story(
        self,
        claims: List[ValidatedCulturalClaim],
        evidence_pack: EvidencePack,
        language: str = "tr"
    ) -> StoryPresentation:
        """Renders a StoryPresentation bound strictly to validated claims."""
        pass


class TemplateStoryCurator(StoryCuratorProvider):
    """
    Deterministic template-driven story curator.
    Renders structured Turkish presentation sections based ONLY on validated claims.
    Operates 100% offline without GPU, cloud API keys, or external network.
    """

    def __init__(self, generator_version: str = SOURCE_BOUND_STORY_SCHEMA_VERSION):
        self.generator_version = generator_version

    def generate_story(
        self,
        claims: List[ValidatedCulturalClaim],
        evidence_pack: EvidencePack,
        language: str = "tr"
    ) -> StoryPresentation:
        story_id = f"story-{uuid.uuid4().hex[:8]}"
        canonical_motif = evidence_pack.subject.canonical_motif_key
        display_name = evidence_pack.subject.display_name

        sections: List[StorySection] = []
        citations: List[StoryCitation] = []
        uncertainty_notes: List[str] = []
        used_claim_ids: List[str] = []
        unused_claim_ids: List[str] = []

        if not claims:
            # Handle empty claim list safely
            sec_id = f"sec-{uuid.uuid4().hex[:6]}"
            sections.append(
                StorySection(
                    section_id=sec_id,
                    heading="Kültürel Anlam Değerlendirmesi",
                    text=f"Mevcut kaynaklar '{display_name}' ({canonical_motif}) motifi için doğrulanmış kültürel anlam veya sembolik iddia sunmamaktadır.",
                    claim_ids=[],
                    citation_ids=[]
                )
            )
            uncertainty_notes.append("Hiçbir doğrulanmış kültürel iddia bulunamadı.")
        else:
            for idx, claim in enumerate(claims):
                used_claim_ids.append(claim.claim_id)
                sec_citations: List[str] = []

                # Build citations from evidence links
                for link in claim.evidence_links:
                    cit_id = f"cit-{uuid.uuid4().hex[:6]}"
                    short_cit = f"{link.source_tier.value} ({link.locator})"
                    citation_obj = StoryCitation(
                        citation_id=cit_id,
                        claim_id=claim.claim_id,
                        evidence_unit_id=link.evidence_unit_id,
                        source_id=self._find_source_for_unit(link.evidence_unit_id, evidence_pack),
                        locator=link.locator,
                        short_citation=short_cit
                    )
                    citations.append(citation_obj)
                    sec_citations.append(cit_id)

                # Render section prose based on categorical claim status
                sec_id = f"sec-{idx+1}"
                if claim.status == CulturalClaimStatus.DOCUMENTED:
                    heading = f"Belgelenmiş İçerik: {claim.canonical_motif_key}"
                    text = f"Kurumsal ve akademik kaynaklarda '{claim.statement}' olarak belgelenmiştir."
                elif claim.status == CulturalClaimStatus.CONTEXTUAL:
                    heading = f"Bağlamsal Yorum: {claim.canonical_motif_key}"
                    scope_desc = self._format_scope(claim)
                    text = f"Bu yorum, kaynaklarda özellikle {scope_desc} bağlamında görülmektedir: {claim.statement}."
                    uncertainty_notes.append(f"İddia '{claim.claim_id}' yalnızca belirli bağlamda geçerlidir.")
                elif claim.status == CulturalClaimStatus.CONTESTED:
                    heading = f"Farklı Görüşler ve Tartışmalar: {claim.canonical_motif_key}"
                    text = f"Kaynaklarda bu konuda farklı görüşler bulunmaktadır: {claim.statement}."
                    uncertainty_notes.append(f"İddia '{claim.claim_id}' hakkında akademik/kurumsal görüş ayrılığı mevcuttur.")
                else:  # UNKNOWN
                    heading = f"Belirsiz Durum: {claim.canonical_motif_key}"
                    text = f"Mevcut kaynaklar '{display_name}' motifi için güvenilir ve kesin bir kültürel anlam kurmaya yetmiyor."
                    uncertainty_notes.append(f"İddia '{claim.claim_id}' için kaynak desteği yetersizdir.")

                sections.append(
                    StorySection(
                        section_id=sec_id,
                        heading=heading,
                        text=text,
                        claim_ids=[claim.claim_id],
                        citation_ids=sec_citations
                    )
                )

        title = f"{display_name} ({canonical_motif}) Kültürel Belge Sunumu"
        summary = (
            f"Bu sunum, '{canonical_motif}' motifi için elde edilen {len(claims)} adet doğrulanmış kültürel iddianın "
            f"kaynaklara dayalı özetidir. ({len(uncertainty_notes)} belirsizlik/bağlam notu içermektedir)."
        )

        provenance = {
            "research_run_id": evidence_pack.research_run_id,
            "subject_id": evidence_pack.subject.subject_id,
            "canonical_motif_key": canonical_motif,
            "policy_version": "story-grounding-policy-v1.0.0",
            "generator_version": self.generator_version
        }

        return StoryPresentation(
            story_id=story_id,
            subject_id=evidence_pack.subject.subject_id,
            canonical_motif_key=canonical_motif,
            title=title,
            summary=summary,
            sections=sections,
            claim_ids=[c.claim_id for c in claims],
            citations=citations,
            uncertainty_notes=uncertainty_notes,
            claims_used=used_claim_ids,
            claims_unused=unused_claim_ids,
            language=language,
            generation_mode="TEMPLATE_ONLY",
            generator_version=self.generator_version,
            provenance=provenance
        )

    def _find_source_for_unit(self, evidence_unit_id: str, evidence_pack: EvidencePack) -> str:
        for unit in evidence_pack.evidence_units:
            if unit.evidence_id == evidence_unit_id:
                return unit.source_id
        return "source-unknown"

    def _format_scope(self, claim: ValidatedCulturalClaim) -> str:
        if not claim.scope:
            return "yerel/belirli"
        parts = []
        if claim.scope.region:
            parts.append(f"bölge: {claim.scope.region}")
        if claim.scope.period:
            parts.append(f"dönem: {claim.scope.period}")
        if claim.scope.tradition:
            parts.append(f"gelenek: {claim.scope.tradition}")
        if claim.scope.institutional_context:
            parts.append(f"kurum: {claim.scope.institutional_context}")
        return ", ".join(parts) if parts else "belirli bağlam"
