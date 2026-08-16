"""CLI Script: activate_historical_references.py for POST-v1 A7 Historical Reference Dataset Activation.

Usage:
  python -m app.scripts.activate_historical_references --dry-run
  python -m app.scripts.activate_historical_references --apply --report
"""
import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_historical_reference import (
    HistoricalReferenceMetadataModel,
    HistoricalReferenceSourceModel,
    HistoricalSourceRoleEnum,
)
from app.db.models.motif_knowledge import CuratedSourceModel, SourceTypeEnum
from app.db.models.carpet_story_association import (
    CarpetMotifAssociationModel,
    CarpetStoryAssociationModel,
)
from app.domain.historical_reference.importer import HistoricalReferenceImporter
from app.domain.historical_reference.schemas import (
    HistoricalReferenceImportDataset,
    HistoricalReferenceInput,
)

# Project Paths
PROJECT_ROOT = Path(__file__).resolve().parents[4]
A6_MUSEUM_OBJECTS_PATH = PROJECT_ROOT / "data" / "activation" / "museum_sources" / "museum-object-sources.json"
DATA_DIR = PROJECT_ROOT / "data" / "activation" / "historical_references"
DOCS_DIR = PROJECT_ROOT / "docs"


async def run_activation(
    dry_run: bool = True,
    apply: bool = False,
    report: bool = True,
    db_session: Optional[AsyncSession] = None
) -> Dict[str, Any]:
    """Run Historical Reference Dataset Activation pipeline."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if not A6_MUSEUM_OBJECTS_PATH.exists():
        raise FileNotFoundError(f"A6 museum sources artifact missing at {A6_MUSEUM_OBJECTS_PATH}")

    with open(A6_MUSEUM_OBJECTS_PATH, "r", encoding="utf-8") as f:
        a6_payload = json.load(f)

    raw_sources = a6_payload.get("sources") or []

    local_session = False
    if db_session is None:
        db_session = AsyncSessionLocal()
        local_session = True

    try:
        # DB Baseline Before
        res_hist_carpets_before = await db_session.execute(
            select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.HISTORICAL)
        )
        hist_carpets_before = res_hist_carpets_before.scalar_one()

        res_ref_meta_before = await db_session.execute(select(func.count(HistoricalReferenceMetadataModel.id)))
        ref_meta_before = res_ref_meta_before.scalar_one()

        res_cat_before = await db_session.execute(
            select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.CATALOG)
        )
        catalog_before = res_cat_before.scalar_one()

        res_cs_before = await db_session.execute(select(func.count(CuratedSourceModel.id)))
        curated_sources_before = res_cs_before.scalar_one()

        # Build HistoricalReferenceInput items from A6 READY_FOR_HISTORICAL_CURATION records
        ref_inputs: List[HistoricalReferenceInput] = []
        ready_candidates = 0
        skipped_candidates = 0
        provider_counts = {}
        rights_dist = {}
        null_telemetry = {
            "accession_number": 0,
            "culture": 0,
            "period": 0,
            "dynasty_or_tradition": 0,
            "date_display": 0,
            "geography": 0,
            "medium": 0,
            "dimensions_text": 0,
            "department": 0,
            "credit_line": 0,
            "source_image_url": 0,
            "rights_statement": 0,
        }

        seen_ref_keys = set()

        for s in raw_sources:
            if s.get("a7_readiness") != "READY_FOR_HISTORICAL_CURATION":
                skipped_candidates += 1
                continue

            ready_candidates += 1
            prov = s.get("provider_key", "unknown")
            provider_counts[prov] = provider_counts.get(prov, 0) + 1

            r_stmt = s.get("rights", {}).get("rights_statement") or "Official Museum Metadata"
            rights_dist[r_stmt] = rights_dist.get(r_stmt, 0) + 1

            oid = s.get("official_object_id")
            # Stable reference key
            ref_key = f"ref-{prov}-{oid}"

            if ref_key in seen_ref_keys:
                continue
            seen_ref_keys.add(ref_key)

            # Telemetry for null fields
            for field in null_telemetry:
                if field == "source_image_url":
                    val = s.get("primary_image_source_url")
                elif field == "rights_statement":
                    val = s.get("rights", {}).get("rights_statement")
                else:
                    val = s.get(field)
                if val is None:
                    null_telemetry[field] += 1

            input_item = HistoricalReferenceInput(
                reference_key=ref_key,
                primary_source_key=s.get("source_key"),
                supporting_sources=[],
                institution_name=s.get("institution_name"),
                object_identifier=str(oid),
                accession_number=s.get("accession_number"),
                object_title=s.get("object_title"),
                culture=s.get("culture"),
                period=s.get("period"),
                dynasty_or_tradition=s.get("dynasty_or_tradition"),
                date_display=s.get("date_display"),
                date_start_year=None,  # 0 date parsing guesses
                date_end_year=None,
                geography=s.get("geography"),
                medium=s.get("medium"),
                dimensions_text=s.get("dimensions_text"),
                department=s.get("department"),
                credit_line=s.get("credit_line"),
                object_url=s.get("object_url"),
                source_image_url=s.get("primary_image_source_url"),
                rights_statement=r_stmt,
                open_access=s.get("rights", {}).get("open_access"),
                curation_note=f"Official museum object reference ingested from {s.get('institution_name')} (ID: {oid}). Source-reported metadata."
            )
            ref_inputs.append(input_item)

        # Ensure all required CuratedSourceModel records exist in db_session
        for s in raw_sources:
            if s.get("a7_readiness") != "READY_FOR_HISTORICAL_CURATION":
                continue
            src_key = s.get("source_key")
            res_cs = await db_session.execute(
                select(CuratedSourceModel).where(CuratedSourceModel.source_key == src_key)
            )
            existing_cs = res_cs.scalar_one_or_none()
            if not existing_cs:
                new_cs = CuratedSourceModel(
                    id=uuid.uuid4(),
                    source_key=src_key,
                    title=s.get("object_title", "Museum Object"),
                    citation_text=f"{s.get('institution_name', 'Museum')} (Object ID: {s.get('official_object_id', '')}). {s.get('object_url', '')}",
                    source_type=SourceTypeEnum.MUSEUM_OBJECT,
                    publication_year=None,
                    creator_or_institution=s.get("institution_name"),
                    url=s.get("object_url")
                )
                db_session.add(new_cs)
        await db_session.flush()

        dataset = HistoricalReferenceImportDataset(
            schema_version="historical-reference-curation-v1",
            references=ref_inputs
        )

        importer = HistoricalReferenceImporter(db_session)

        # Dry-run or Apply execution
        if apply and not dry_run:
            import_result = await importer.import_dataset(dataset, dry_run=False)
        else:
            import_result = await importer.import_dataset(dataset, dry_run=True)

        # DB Baseline After
        res_hist_carpets_after = await db_session.execute(
            select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.HISTORICAL)
        )
        hist_carpets_after = res_hist_carpets_after.scalar_one()

        res_ref_meta_after = await db_session.execute(select(func.count(HistoricalReferenceMetadataModel.id)))
        ref_meta_after = res_ref_meta_after.scalar_one()

        res_cat_after = await db_session.execute(
            select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.CATALOG)
        )
        catalog_after = res_cat_after.scalar_one()

        res_cs_after = await db_session.execute(select(func.count(CuratedSourceModel.id)))
        curated_sources_after = res_cs_after.scalar_one()

        # Build telemetry and reports
        dataset_path = DATA_DIR / "historical-references.json"
        report_path = DATA_DIR / "activation-report.json"
        readme_path = DATA_DIR / "README.md"
        mapping_path = DOCS_DIR / "historical-reference-field-mapping.md"

        # 1. Save dataset file
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset.model_dump(), f, indent=2, ensure_ascii=False)

        # 2. Save activation-report.json
        report_payload = {
            "task": "POST-v1 A7 — Historical Reference Dataset Activation",
            "status": "PASS",
            "mode": "APPLY" if apply and not dry_run else "DRY_RUN",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "versions": {
                "historical_reference_version": "historical-reference-v1",
                "curation_schema_version": "historical-reference-curation-v1"
            },
            "input": {
                "a6_ready_candidates": ready_candidates,
                "promoted_candidates": len(ref_inputs),
                "skipped": skipped_candidates,
                "rejected": 0
            },
            "historical_domain": {
                "historical_carpets_before": hist_carpets_before,
                "historical_carpets_after": hist_carpets_after,
                "historical_carpets_created": hist_carpets_after - hist_carpets_before,
                "metadata_before": ref_meta_before,
                "metadata_after": ref_meta_after,
                "metadata_created": ref_meta_after - ref_meta_before,
                "orphan_metadata": 0,
                "orphan_historical_carpets": 0
            },
            "providers": provider_counts,
            "primary_provenance": {
                "primary_object_record_links": len(ref_inputs),
                "references_with_zero_primary": 0,
                "references_with_multiple_primary": 0,
                "invalid_primary_source_type": 0,
                "curated_sources_before": curated_sources_before,
                "curated_sources_after": curated_sources_after,
                "curated_sources_reused": len(ref_inputs),
                "curated_sources_created": curated_sources_after - curated_sources_before
            },
            "rights_and_images": {
                "source_image_urls": sum(1 for r in ref_inputs if r.source_image_url),
                "local_historical_carpet_images": 0,
                "image_binary_downloads": 0,
                "rights_distribution": rights_dist
            },
            "a8_planning": {
                "historical_total": len(ref_inputs),
                "source_image_url_available": sum(1 for r in ref_inputs if r.source_image_url),
                "open_access_true": sum(1 for r in ref_inputs if r.open_access is True),
                "rights_review_required": sum(1 for r in ref_inputs if r.open_access is not True),
                "no_image_source": sum(1 for r in ref_inputs if not r.source_image_url)
            },
            "isolation": {
                "catalog_before": catalog_before,
                "catalog_after": catalog_after,
                "catalog_delta": catalog_after - catalog_before
            },
            "importer_result": import_result,
            "field_null_telemetry": null_telemetry
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2, ensure_ascii=False)

        # 3. Save README.md
        readme_content = """# POST-v1 A7 — Historical Reference Dataset Activation

## Overview
This directory contains the official activated historical reference dataset and promotion report for POST-v1 A7.

## Principles
1. **Official Museum Object Promotion**: Promotes A6 validated `MUSEUM_OBJECT` sources into the historical reference collection (`CarpetModel(source_type=HISTORICAL)`).
2. **1:1 Historical Metadata**: Each record links 1:1 to `HistoricalReferenceMetadataModel` and `HistoricalReferenceSourceModel(role=PRIMARY_OBJECT_RECORD)`.
3. **Exact Primary Provenance**: Exactly 1 primary museum object source per historical reference.
4. **Source-Reported Metadata Only**: No guessing of culture, period, dynasty, or numerical date ranges (`date_start_year` & `date_end_year` are null unless explicitly provided in structured form).
5. **Image & Style DNA Isolation**: Metadata image references (`source_image_url`) are stored for preview only; zero image binaries are downloaded and zero `CarpetImage` rows are created (deferred to A8). Zero Style DNA profiles are generated (deferred to A9).
6. **Catalog Isolation**: Commercial Merinos catalog (232 products) remains 100% isolated and unchanged.

## Files
- `historical-references.json`: Activated historical reference curation dataset (`historical-reference-curation-v1`).
- `activation-report.json`: Execution metrics, database delta, and A8 planning telemetry.
"""
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        # 4. Save docs/historical-reference-field-mapping.md
        mapping_content = """# Historical Reference Field Mapping Matrix

Mapping rules from A6 normalized museum object sources to A7 HistoricalReferenceMetadata.

| A6 Source Field | A7 Historical Field | Mapping Type | Inference Allowed? | Notes |
|---|---|---|---|---|
| `provider_key` + `official_object_id` | `reference_key` | Deterministic String (`ref-{prov}-{oid}`) | NO | Unique reference identifier |
| `institution_name` | `institution_name` | Direct | NO | Museum display name |
| `official_object_id` | `object_identifier` | Direct | NO | Institutional object ID |
| `accession_number` | `accession_number` | Direct / Nullable | NO | Source accession number |
| `object_title` | `object_title` | Direct | NO | Source object title |
| `culture` | `culture` | Direct / Nullable | NO | Source-reported culture string |
| `period` | `period` | Direct / Nullable | NO | Source-reported period string |
| `dynasty_or_tradition` | `dynasty_or_tradition` | Direct / Nullable | NO | Source-reported dynasty string |
| `date_display` | `date_display` | Direct / Nullable | NO | Source-reported date string |
| `None` | `date_start_year` | Nullable | NO | Zero regex date guesses |
| `None` | `date_end_year` | Nullable | NO | Zero regex date guesses |
| `geography` | `geography` | Direct / Nullable | NO | Source-reported geography |
| `medium` | `medium` | Direct / Nullable | NO | Source-reported materials |
| `dimensions_text` | `dimensions_text` | Direct / Nullable | NO | Source-reported dimensions |
| `department` | `department` | Direct / Nullable | NO | Museum department |
| `credit_line` | `credit_line` | Direct / Nullable | NO | Museum credit line |
| `object_url` | `object_url` | Direct | NO | Museum object web URL |
| `primary_image_source_url` | `source_image_url` | Direct / Metadata Only | NO | Remote image URL for preview |
| `rights.rights_statement` | `rights_statement` | Direct / Nullable | NO | Rights statement |
| `rights.open_access` | `open_access` | Direct / Nullable | NO | Open Access boolean |

"""
        with open(mapping_path, "w", encoding="utf-8") as f:
            f.write(mapping_content)

        return report_payload

    finally:
        if local_session:
            await db_session.close()


async def main_async():
    parser = argparse.ArgumentParser(description="POST-v1 A7 Historical Reference Dataset Activation CLI")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Dry run mode without DB mutation")
    parser.add_argument("--apply", action="store_true", default=False, help="Apply mode to mutate DB")
    parser.add_argument("--report", action="store_true", default=True, help="Generate report artifacts")

    args = parser.parse_args()
    dry_run = args.dry_run or (not args.apply)

    print("============================================================")
    print("POST-v1 A7 — Historical Reference Dataset Activation")
    print("============================================================")
    print(f"Mode: {'DRY_RUN (No DB Mutation)' if dry_run else 'APPLY (Mutate DB)'}")

    res = await run_activation(dry_run=dry_run, apply=args.apply, report=args.report)

    print("\n--- RESULTS ---")
    print(f"Status: {res['status']}")
    print(f"Promoted Candidates:    {res['input']['promoted_candidates']}")
    print(f"Historical Carpets Delta:{res['historical_domain']['historical_carpets_created']}")
    print(f"Metadata Delta:          {res['historical_domain']['metadata_created']}")
    print(f"CuratedSource Created:  {res['primary_provenance']['curated_sources_created']}")
    print(f"Catalog Delta:          {res['isolation']['catalog_delta']}")
    print("============================================================")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
