"""CLI script for inspecting external carpet dataset corpora and producing manifests & quality reports.

Usage:
python -m app.scripts.inspect_external_carpet_dataset \\
  --dataset-key iranian-patterns \\
  --input-dir data/external_datasets/raw/iranian-patterns \\
  --provider-type KAGGLE \\
  --source-url "https://www.kaggle.com/datasets/..." \\
  --license-name "CC-BY-4.0" \\
  --license-verified \\
  --output-manifest data/external_datasets/manifests/iranian-patterns.jsonl \\
  --output-report data/external_datasets/reports/iranian-patterns-report.json
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from app.core.config import settings
from app.domain.external_datasets.schemas import DatasetProviderType, ImageValidationStatus
from app.domain.external_datasets.adapters import LocalDirectoryDatasetAdapter


def get_db_counts() -> dict:
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if not Path(db_path).exists():
        return {
            "carpet_count": 0,
            "carpet_image_count": 0,
            "historical_reference_count": 0,
            "style_profile_count": 0,
        }
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    counts = {
        "carpet_count": cur.execute("SELECT COUNT(*) FROM carpets").fetchone()[0],
        "carpet_image_count": cur.execute("SELECT COUNT(*) FROM carpet_images").fetchone()[0],
        "historical_reference_count": cur.execute("SELECT COUNT(*) FROM historical_reference_metadata").fetchone()[0],
        "style_profile_count": cur.execute("SELECT COUNT(*) FROM carpet_style_profiles").fetchone()[0],
    }
    conn.close()
    return counts


def main():
    parser = argparse.ArgumentParser(description="Inspect external carpet dataset corpora.")
    parser.add_argument("--dataset-key", required=True, help="Unique slug e.g. iranian-patterns")
    parser.add_argument("--input-dir", required=True, help="Path to raw dataset directory")
    parser.add_argument("--provider-type", required=True, type=str, help="Provider type e.g. KAGGLE, MUSEUM, OFFICIAL_MANUFACTURER")
    parser.add_argument("--source-url", default="", help="Original source homepage or URL")
    parser.add_argument("--license-name", default="Unknown", help="License name")
    parser.add_argument("--license-verified", action="store_true", help="Set if license permits promotion")
    parser.add_argument("--manufacturer", default=None, help="Manufacturer name if OFFICIAL_MANUFACTURER")
    parser.add_argument("--institution", default=None, help="Institution name if MUSEUM")
    parser.add_argument("--strict", action="store_true", help="Fail with non-zero exit code if invalid images found")
    parser.add_argument("--output-manifest", default=None, help="Path to write output .jsonl manifest")
    parser.add_argument("--output-report", default=None, help="Path to write output .json report")

    args = parser.parse_args()

    # Verify DB immutability baseline
    initial_counts = get_db_counts()


    provider_enum = DatasetProviderType[args.provider_type.upper()]

    adapter = LocalDirectoryDatasetAdapter(
        dataset_key=args.dataset_key,
        input_dir=Path(args.input_dir),
        provider_type=provider_enum,
        source_url=args.source_url,
        license_name=args.license_name,
        license_verified=args.license_verified,
        manufacturer=args.manufacturer,
        institution=args.institution,
    )

    records, report = adapter.inspect_and_build_manifest()

    print(f"=" * 60)
    print(f"EXTERNAL DATASET INTAKE & CLASSIFICATION: {args.dataset_key}")
    print(f"=" * 60)
    print(f"Provider Type:      {report.provider_type.value}")
    print(f"Observed Images:    {report.observed_count}")
    print(f"Valid Images:       {report.valid_images}")
    print(f"Invalid Images:     {report.invalid_images}")
    print(f"Exact Duplicates:   {report.exact_duplicate_count}")
    print(f"Role Distribution:  {json.dumps(report.role_distribution, indent=2)}")
    print(f"Catalog Eligible:   {report.catalog_eligible_count}")
    print(f"Historical Cand.:   {report.historical_candidate_count}")
    print(f"Quarantine Count:   {report.quarantine_count}")
    print(f"Readiness:          {report.promotion_readiness}")
    print(f"-" * 60)

    # Output manifest if requested
    if args.output_manifest:
        out_p = Path(args.output_manifest)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            for r in records:
                f.write(r.model_dump_json() + "\n")
        print(f"[MANIFEST SAVED]: {out_p}")

    # Output report if requested
    if args.output_report:
        rep_p = Path(args.output_report)
        rep_p.parent.mkdir(parents=True, exist_ok=True)
        with open(rep_p, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        print(f"[REPORT SAVED]:   {rep_p}")

    # Assert DB counts remain unchanged
    final_counts = get_db_counts()

    assert initial_counts == final_counts, f"DB counts changed during dataset inspection! Initial: {initial_counts}, Final: {final_counts}"
    print("[DB IMMUTABILITY ASSERTION]: PASS (0 DB rows inserted/deleted)")

    if args.strict and report.invalid_images > 0:
        print(f"[STRICT CHECK FAILED]: Found {report.invalid_images} invalid image(s)!")
        sys.exit(1)

    print("[STATUS]: SUCCESS")


if __name__ == "__main__":
    main()
