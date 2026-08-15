"""Pure projector for mapping carpet story associations to 8 theme support states."""
from dataclasses import dataclass, field
from typing import Dict, List, Any
from app.db.models.carpet_story_association import CarpetStoryAssociationModel
from app.db.models.carpet_narrative_affinity import ThemeSupportStatusEnum
from app.db.models.motif_knowledge import MotifStoryStatusEnum
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES


@dataclass
class ThemeSupportProjection:
    theme_key: str
    carpet_support_status: ThemeSupportStatusEnum
    has_contested_evidence: bool
    documented_claim_keys: List[str] = field(default_factory=list)
    contextual_claim_keys: List[str] = field(default_factory=list)
    contested_claim_keys: List[str] = field(default_factory=list)
    story_associations: List[CarpetStoryAssociationModel] = field(default_factory=list)

    def to_evidence_dict(self) -> Dict[str, Any]:
        return {
            "documented_claim_keys": self.documented_claim_keys,
            "contextual_claim_keys": self.contextual_claim_keys,
            "contested_claim_keys": self.contested_claim_keys,
            "story_association_ids": [str(sa.id) for sa in self.story_associations]
        }


class CarpetNarrativeEvidenceProjector:
    """Projects explicit CarpetStoryAssociations to 8 canonical narrative theme support states."""

    @staticmethod
    def project_evidence(story_associations: List[CarpetStoryAssociationModel]) -> Dict[str, ThemeSupportProjection]:
        projections: Dict[str, ThemeSupportProjection] = {}

        # Initialize all 8 canonical themes with NO_EVIDENCE
        for t in CANONICAL_NARRATIVE_THEMES:
            key = t["key"]
            projections[key] = ThemeSupportProjection(
                theme_key=key,
                carpet_support_status=ThemeSupportStatusEnum.NO_EVIDENCE,
                has_contested_evidence=False
            )

        # Process each explicit story association
        for sa in story_associations:
            claim = sa.claim
            if not claim or claim.status == MotifStoryStatusEnum.UNKNOWN:
                # Defensive rule: UNKNOWN claims or missing claims provide 0 evidence
                continue

            for theme in claim.themes:
                t_key = theme.theme_key
                if t_key not in projections:
                    continue

                proj = projections[t_key]
                if sa not in proj.story_associations:
                    proj.story_associations.append(sa)

                c_key = claim.claim_key
                if claim.status == MotifStoryStatusEnum.DOCUMENTED:
                    if c_key not in proj.documented_claim_keys:
                        proj.documented_claim_keys.append(c_key)
                elif claim.status == MotifStoryStatusEnum.CONTEXTUAL:
                    if c_key not in proj.contextual_claim_keys:
                        proj.contextual_claim_keys.append(c_key)
                elif claim.status == MotifStoryStatusEnum.CONTESTED:
                    if c_key not in proj.contested_claim_keys:
                        proj.contested_claim_keys.append(c_key)
                    proj.has_contested_evidence = True

        # Derive primary carpet_support_status for each theme
        for key, proj in projections.items():
            if proj.documented_claim_keys:
                proj.carpet_support_status = ThemeSupportStatusEnum.DOCUMENTED
            elif proj.contextual_claim_keys:
                proj.carpet_support_status = ThemeSupportStatusEnum.CONTEXTUAL
            elif proj.contested_claim_keys:
                proj.carpet_support_status = ThemeSupportStatusEnum.CONTESTED_ONLY
            else:
                proj.carpet_support_status = ThemeSupportStatusEnum.NO_EVIDENCE

        return projections
