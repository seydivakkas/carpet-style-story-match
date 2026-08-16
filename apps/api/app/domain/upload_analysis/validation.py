"""
Taxonomy & Ontology Validation Engine (v1.0.0).

Performs deterministic validation of Visual Category Taxonomy and Motif Ontology.
Checks for duplicate keys, label completeness, valid references, and contract integrity.
"""
from typing import List, Dict, Any
from app.domain.upload_analysis.visual_categories import (
    CANONICAL_VISUAL_CATEGORIES,
    VISUAL_CATEGORY_TAXONOMY_VERSION,
    VisualCategoryKey,
)
from app.domain.upload_analysis.motif_ontology import (
    MOTIF_ONTOLOGY_DEFINITIONS,
    MOTIF_ONTOLOGY_VERSION,
    CANONICAL_PRODUCTION_MOTIFS,
    VisualCandidateKey,
    DetectionMode,
)
from app.domain.upload_analysis.schemas import UploadAnalysisResult


class TaxonomyValidationError(ValueError):
    """Raised when taxonomy or ontology validation fails."""
    pass


ContractValidationError = TaxonomyValidationError


def validate_visual_category_key(key: str) -> bool:
    """Validate that visual category key exists in canonical taxonomy."""
    valid_keys = {e.value for e in VisualCategoryKey}
    if key not in valid_keys:
        raise TaxonomyValidationError(f"Invalid visual category key: '{key}'. Must be one of {valid_keys}")
    return True


def validate_visual_candidate_key(key: str) -> bool:
    """Validate that visual candidate key exists in candidate taxonomy."""
    valid_keys = {e.value for e in VisualCandidateKey}
    if key not in valid_keys:
        raise TaxonomyValidationError(f"Invalid visual candidate key: '{key}'. Must be one of {valid_keys}")
    return True


def validate_upload_analysis_result(result: UploadAnalysisResult) -> Dict[str, Any]:
    """Validate complete UploadAnalysisResult domain contract."""
    validate_visual_category_key(result.visual_category.category_key)
    for mc in result.motif_candidates:
        validate_visual_candidate_key(mc.visual_candidate_key)
    return {"valid": True, "analysis_id": result.analysis_id}


def validate_visual_category_taxonomy() -> Dict[str, Any]:
    """Validate Visual Category Taxonomy v1.0.0 integrity."""
    keys_seen = set()
    for cat in CANONICAL_VISUAL_CATEGORIES:
        key = cat.get("category_key")
        if not key:
            raise TaxonomyValidationError("Visual category definition missing 'category_key'.")
        if key in keys_seen:
            raise TaxonomyValidationError(f"Duplicate visual category key detected: '{key}'.")
        keys_seen.add(key)

        if not cat.get("label_tr"):
            raise TaxonomyValidationError(f"Visual category '{key}' missing 'label_tr'.")
        if not cat.get("label_en"):
            raise TaxonomyValidationError(f"Visual category '{key}' missing 'label_en'.")

    # Ensure all enum keys are present
    enum_keys = {e.value for e in VisualCategoryKey}
    if keys_seen != enum_keys:
        missing = enum_keys - keys_seen
        raise TaxonomyValidationError(f"Visual category taxonomy missing enum keys: {missing}")

    return {
        "valid": True,
        "taxonomy_version": VISUAL_CATEGORY_TAXONOMY_VERSION,
        "total_categories": len(CANONICAL_VISUAL_CATEGORIES)
    }


def validate_motif_ontology() -> Dict[str, Any]:
    """Validate Motif Ontology v1.0.0 integrity and canonical mapping consistency."""
    canonical_keys_seen = set()
    candidate_keys_referenced = set()

    for entry in MOTIF_ONTOLOGY_DEFINITIONS:
        ckey = entry.get("canonical_key")
        if not ckey:
            raise TaxonomyValidationError("Motif ontology entry missing 'canonical_key'.")
        if ckey in canonical_keys_seen:
            raise TaxonomyValidationError(f"Duplicate canonical motif key detected: '{ckey}'.")
        canonical_keys_seen.add(ckey)

        # Must be in 13 production canonical motifs
        if ckey not in CANONICAL_PRODUCTION_MOTIFS:
            raise TaxonomyValidationError(f"Canonical motif '{ckey}' is not in production motif set.")

        if not entry.get("display_name_tr"):
            raise TaxonomyValidationError(f"Motif ontology entry '{ckey}' missing 'display_name_tr'.")

        v_keys = entry.get("visual_candidate_keys", [])
        if not v_keys:
            raise TaxonomyValidationError(f"Motif ontology entry '{ckey}' must reference at least one visual candidate key.")

        for vk in v_keys:
            candidate_keys_referenced.add(vk)

        d_mode = entry.get("detection_mode")
        if d_mode not in {e.value for e in DetectionMode}:
            raise TaxonomyValidationError(f"Invalid detection mode '{d_mode}' in motif '{ckey}'.")

        version = entry.get("ontology_version")
        if version != MOTIF_ONTOLOGY_VERSION:
            raise TaxonomyValidationError(f"Invalid ontology version '{version}' in motif '{ckey}'.")

    # Ensure all 13 canonical motifs are defined
    missing_production = set(CANONICAL_PRODUCTION_MOTIFS) - canonical_keys_seen
    if missing_production:
        raise TaxonomyValidationError(f"Motif ontology missing production motifs: {missing_production}")

    return {
        "valid": True,
        "ontology_version": MOTIF_ONTOLOGY_VERSION,
        "total_motifs": len(MOTIF_ONTOLOGY_DEFINITIONS),
        "referenced_candidate_keys": len(candidate_keys_referenced)
    }


def validate_all_taxonomies() -> Dict[str, Any]:
    """Run full validation suite for visual categories and motif ontology."""
    v_res = validate_visual_category_taxonomy()
    m_res = validate_motif_ontology()
    return {
        "status": "PASS",
        "visual_taxonomy": v_res,
        "motif_ontology": m_res
    }
