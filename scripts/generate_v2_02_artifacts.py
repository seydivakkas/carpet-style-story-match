"""
Artifact Generator for V2-02 User Upload Analysis Contract & Taxonomies.
Generates:
  - data/taxonomies/visual-category-taxonomy-v1.json
  - data/taxonomies/motif-ontology-v1.json
  - data/schemas/upload-analysis-v1.schema.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

from app.domain.upload_analysis.visual_categories import (
    CANONICAL_VISUAL_CATEGORIES,
    VISUAL_CATEGORY_TAXONOMY_VERSION,
)
from app.domain.upload_analysis.motif_ontology import (
    MOTIF_ONTOLOGY_DEFINITIONS,
    MOTIF_ONTOLOGY_VERSION,
    CANONICAL_PRODUCTION_MOTIFS,
)
from app.domain.upload_analysis.schemas import UploadAnalysisResult


def main():
    root_dir = Path(__file__).resolve().parent.parent

    # 1. Visual Category Taxonomy JSON
    taxonomies_dir = root_dir / "data" / "taxonomies"
    taxonomies_dir.mkdir(parents=True, exist_ok=True)

    v_cat_file = taxonomies_dir / "visual-category-taxonomy-v1.json"
    v_cat_data = {
        "taxonomy_version": VISUAL_CATEGORY_TAXONOMY_VERSION,
        "total_categories": len(CANONICAL_VISUAL_CATEGORIES),
        "categories": CANONICAL_VISUAL_CATEGORIES
    }
    v_cat_file.write_text(json.dumps(v_cat_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated: {v_cat_file}")

    # 2. Motif Ontology JSON
    m_ont_file = taxonomies_dir / "motif-ontology-v1.json"
    m_ont_data = {
        "ontology_version": MOTIF_ONTOLOGY_VERSION,
        "total_motifs": len(MOTIF_ONTOLOGY_DEFINITIONS),
        "canonical_production_motifs": CANONICAL_PRODUCTION_MOTIFS,
        "motifs": MOTIF_ONTOLOGY_DEFINITIONS
    }
    m_ont_file.write_text(json.dumps(m_ont_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated: {m_ont_file}")

    # 3. JSON Schema for UploadAnalysisResult
    schemas_dir = root_dir / "data" / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)

    schema_file = schemas_dir / "upload-analysis-v1.schema.json"
    json_schema = UploadAnalysisResult.model_json_schema()
    json_schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    json_schema["title"] = "UploadAnalysisResultContract"
    json_schema["version"] = "upload-analysis-v1.0.0"

    schema_file.write_text(json.dumps(json_schema, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated: {schema_file}")


if __name__ == "__main__":
    main()
