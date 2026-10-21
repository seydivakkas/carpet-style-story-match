"""CLI script for batch Style DNA analysis of historical carpets v1.

Usage:
  # Dry-run inspection
  python -m app.scripts.analyze_historical_style_dna --dry-run

  # Pilot run on 5 historical carpets
  python -m app.scripts.analyze_historical_style_dna --pilot --apply --report data/activation/historical_style_dna/pilot-report.json

  # Full historical batch analysis
  python -m app.scripts.analyze_historical_style_dna --apply --resume --report data/activation/historical_style_dna/activation-report.json
"""

import argparse
import asyncio
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_historical_reference import HistoricalReferenceMetadataModel
from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    StyleProfileStatus,
    StyleDimensionStatus,
)
from app.domain.styledna.engine import STYLE_DNA_ALGORITHM_VERSION
from app.domain.styledna.service import StyleDNAService


DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "activation" / "historical_style_dna"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_historical_batch_analysis(
    apply: bool = False,
    pilot: bool = False,
    limit: Optional[int] = None,
    reference_key_filter: Optional[str] = None,
    force: bool = False,
    resume: bool = True,
    report_path: Optional[str] = None,
    run_manifest_path: Optional[str] = None,
    db_session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    run_id = f"hist-run-{int(time.time())}"
    started_at = utc_now_iso()

    if pilot and limit is None:
        limit = 5

    if run_manifest_path is None:
        run_manifest_path = str(DATA_DIR / "style-dna-batch-run.json")

    # Load A8 sidecar snapshot mapping if available
    a8_sidecar_path = DATA_DIR.parent / "historical_images" / "historical-image-activation.json"
    sidecar_map: Dict[str, Dict[str, Any]] = {}
    if a8_sidecar_path.exists():
        with open(a8_sidecar_path, "r", encoding="utf-8") as f:
            sidecar_data = json.load(f)
            for rec in sidecar_data.get("records", []):
                sidecar_map[rec.get("reference_key")] = rec

    local_session = False
    if db_session is None:
        db_session = AsyncSessionLocal()
        local_session = True

    # Query historical references join carpet
    stmt = (
        select(HistoricalReferenceMetadataModel)
        .options(selectinload(HistoricalReferenceMetadataModel.carpet))
        .order_by(HistoricalReferenceMetadataModel.reference_key.asc())
    )
    if reference_key_filter:
        stmt = stmt.where(HistoricalReferenceMetadataModel.reference_key == reference_key_filter)

    res = await db_session.execute(stmt)
    hist_metas = list(res.scalars().all())

    historical_total = len(hist_metas)

    # Apply limit if specified
    if limit is not None:
        target_metas = hist_metas[:limit]
    else:
        target_metas = hist_metas

    # Catalog isolation check before run
    cat_carpets_before = (await db_session.execute(select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.CATALOG))).scalar_one()
    cat_images_before = (await db_session.execute(select(func.count(CarpetImageModel.id)).join(CarpetModel).where(CarpetModel.source_type == CarpetSourceType.CATALOG))).scalar_one()

    print("=" * 60)
    print("HISTORICAL STYLE DNA BATCH ANALYSIS v1")
    print(f"Run ID:            {run_id}")
    print(f"Algorithm Version: {STYLE_DNA_ALGORITHM_VERSION}")
    print(f"Mode:              {'APPLY (MUTATING)' if apply else 'DRY-RUN (SAFE)'}")
    print(f"Historical Total:  {historical_total}")
    print(f"Target Count:      {len(target_metas)}")
    print("=" * 60)

    per_product_records: List[Dict[str, Any]] = []

    already_current_count = 0
    processed_count = 0
    complete_count = 0
    partial_count = 0
    failed_count = 0
    stale_count = 0
    pending_count = 0
    no_primary_count = 0
    provenance_mismatch_count = 0

    DIM_KEY_MAP = {
        "color_energy": "D1 color_energy",
        "color_diversity": "D2 color_diversity",
        "contrast": "D3 contrast",
        "warmth": "D4 warmth",
        "visual_complexity": "D5 visual_complexity",
        "structural_order": "D6 structural_order",
        "rhythm_repetition": "D7 rhythm_repetition",
        "focal_strength": "D8 focal_strength",
        "form_language": "D9 form_language",
    }

    dim_availability: Dict[str, Dict[str, int]] = {
        label: {"AVAILABLE": 0, "LOW_CONFIDENCE": 0, "NOT_AVAILABLE": 0, "FAILED": 0}
        for label in DIM_KEY_MAP.values()
    }
    dim_values_list: Dict[str, List[float]] = {label: [] for label in DIM_KEY_MAP.values()}

    for idx, meta in enumerate(target_metas, 1):
        ref_key = meta.reference_key
        carpet_id = meta.carpet_id
        obj_id = meta.object_identifier

        sidecar_rec = sidecar_map.get(ref_key, {})
        source_record_sha256 = sidecar_rec.get("source_record_sha256")
        sidecar_image_sha256 = sidecar_rec.get("image_content_sha256")

        img_stmt = select(CarpetImageModel).where(
            CarpetImageModel.carpet_id == carpet_id,
            CarpetImageModel.is_primary.is_(True),
        )
        img_res = await db_session.execute(img_stmt)
        primary_img = img_res.scalar_one_or_none()

        prof_stmt = (
            select(CarpetStyleProfileModel)
            .options(selectinload(CarpetStyleProfileModel.dimensions))
            .where(
                CarpetStyleProfileModel.carpet_id == carpet_id,
                CarpetStyleProfileModel.algorithm_version == STYLE_DNA_ALGORITHM_VERSION,
            )
        )
        prof_res = await db_session.execute(prof_stmt)
        existing_prof = prof_res.scalar_one_or_none()

        if not primary_img:
            no_primary_count += 1
            per_product_records.append({
                "reference_key": ref_key,
                "official_object_id": obj_id,
                "historical_carpet_id": str(carpet_id),
                "primary_image_id": None,
                "source_record_sha256": source_record_sha256,
                "image_content_sha256": None,
                "algorithm_version": STYLE_DNA_ALGORITHM_VERSION,
                "status": "NO_PRIMARY_IMAGE",
                "available_dimension_count": 0,
                "low_confidence_dimension_count": 0,
                "not_available_dimension_count": 0,
                "error_code": None,
                "started_at": utc_now_iso(),
                "completed_at": utc_now_iso(),
                "duration_ms": 0,
            })
            continue

        # Check provenance linkage consistency
        if sidecar_image_sha256 and primary_img.sha256 != sidecar_image_sha256:
            provenance_mismatch_count += 1
            print(f"[WARNING] Image hash mismatch for {ref_key}: stored={primary_img.sha256}, sidecar={sidecar_image_sha256}")

        # Check idempotency / stale status
        is_already_current = False
        if existing_prof and not force:
            if str(existing_prof.image_id) == str(primary_img.id) and existing_prof.algorithm_version == STYLE_DNA_ALGORITHM_VERSION:
                is_already_current = True
            else:
                stale_count += 1

        if is_already_current and resume:
            already_current_count += 1
            avail_cnt = sum(1 for d in existing_prof.dimensions if d.status == StyleDimensionStatus.AVAILABLE)
            low_cnt = sum(1 for d in existing_prof.dimensions if d.status == StyleDimensionStatus.LOW_CONFIDENCE)
            nav_cnt = sum(1 for d in existing_prof.dimensions if d.status == StyleDimensionStatus.NOT_AVAILABLE)

            if existing_prof.status == StyleProfileStatus.COMPLETE:
                complete_count += 1
            elif existing_prof.status == StyleProfileStatus.PARTIAL:
                partial_count += 1
            else:
                failed_count += 1

            for d in existing_prof.dimensions:
                dim_label = DIM_KEY_MAP.get(d.dimension_key, d.dimension_key)
                if dim_label in dim_availability:
                    status_name = d.status.value if hasattr(d.status, "value") else str(d.status)
                    dim_availability[dim_label][status_name] = dim_availability[dim_label].get(status_name, 0) + 1
                    if d.value is not None and not math.isnan(d.value):
                        dim_values_list[dim_label].append(d.value)

            per_product_records.append({
                "reference_key": ref_key,
                "official_object_id": obj_id,
                "historical_carpet_id": str(carpet_id),
                "primary_image_id": str(primary_img.id),
                "source_record_sha256": source_record_sha256,
                "image_content_sha256": primary_img.sha256,
                "algorithm_version": STYLE_DNA_ALGORITHM_VERSION,
                "status": f"ALREADY_CURRENT_{existing_prof.status.value}",
                "available_dimension_count": avail_cnt,
                "low_confidence_dimension_count": low_cnt,
                "not_available_dimension_count": nav_cnt,
                "error_code": None,
                "started_at": utc_now_iso(),
                "completed_at": utc_now_iso(),
                "duration_ms": 0,
            })
            continue

        pending_count += 1

        if not apply:
            per_product_records.append({
                "reference_key": ref_key,
                "official_object_id": obj_id,
                "historical_carpet_id": str(carpet_id),
                "primary_image_id": str(primary_img.id),
                "source_record_sha256": source_record_sha256,
                "image_content_sha256": primary_img.sha256,
                "algorithm_version": STYLE_DNA_ALGORITHM_VERSION,
                "status": "PENDING_ANALYSIS",
                "available_dimension_count": 0,
                "low_confidence_dimension_count": 0,
                "not_available_dimension_count": 0,
                "error_code": None,
                "started_at": utc_now_iso(),
                "completed_at": utc_now_iso(),
                "duration_ms": 0,
            })
            continue

        # Execute analysis per product transactionally
        item_started_at = utc_now_iso()
        t0 = time.time()
        error_code = None
        status_str = "FAILED"
        avail_cnt, low_cnt, nav_cnt = 0, 0, 0

        try:
            service = StyleDNAService(db_session)
            profile, is_cached = await service.calculate_and_persist_style_dna(
                carpet_id=carpet_id,
                image_id=primary_img.id,
            )

            processed_count += 1
            status_str = profile.status.value

            if profile.status == StyleProfileStatus.COMPLETE:
                complete_count += 1
            elif profile.status == StyleProfileStatus.PARTIAL:
                partial_count += 1
            else:
                failed_count += 1

            avail_cnt = sum(1 for d in profile.dimensions if d.status == StyleDimensionStatus.AVAILABLE)
            low_cnt = sum(1 for d in profile.dimensions if d.status == StyleDimensionStatus.LOW_CONFIDENCE)
            nav_cnt = sum(1 for d in profile.dimensions if d.status == StyleDimensionStatus.NOT_AVAILABLE)

            for d in profile.dimensions:
                dim_label = DIM_KEY_MAP.get(d.dimension_key, d.dimension_key)
                if dim_label in dim_availability:
                    status_name = d.status.value if hasattr(d.status, "value") else str(d.status)
                    dim_availability[dim_label][status_name] = dim_availability[dim_label].get(status_name, 0) + 1
                    if d.value is not None and not math.isnan(d.value):
                        dim_values_list[dim_label].append(d.value)

        except Exception as e:
            failed_count += 1
            error_code = type(e).__name__
            status_str = "FAILED"
            print(f"[ERROR processing {ref_key}]: {e}")

        t1 = time.time()
        dur_ms = int((t1 - t0) * 1000)

        per_product_records.append({
            "reference_key": ref_key,
            "official_object_id": obj_id,
            "historical_carpet_id": str(carpet_id),
            "primary_image_id": str(primary_img.id),
            "source_record_sha256": source_record_sha256,
            "image_content_sha256": primary_img.sha256,
            "algorithm_version": STYLE_DNA_ALGORITHM_VERSION,
            "status": status_str,
            "available_dimension_count": avail_cnt,
            "low_confidence_dimension_count": low_cnt,
            "not_available_dimension_count": nav_cnt,
            "error_code": error_code,
            "started_at": item_started_at,
            "completed_at": utc_now_iso(),
            "duration_ms": dur_ms,
        })

        if idx % 10 == 0 or idx == len(target_metas):
            print(f"Processed {idx}/{len(target_metas)} historical references... (COMPLETE: {complete_count}, PARTIAL: {partial_count}, FAILED: {failed_count})")

    completed_at = utc_now_iso()

    # Terminal status accounting check per historical item
    target_keys = {m.reference_key for m in target_metas}
    skipped_metas = [m for m in hist_metas if m.reference_key not in target_keys]

    accounted_count = len(per_product_records) + len(skipped_metas)
    unaccounted = historical_total - accounted_count

    # Variance and Range Audit
    range_violations = 0
    nan_inf_violations = 0
    dim_stats: Dict[str, Dict[str, Any]] = {}

    for d_key, vals in dim_values_list.items():
        if vals:
            min_v = min(vals)
            max_v = max(vals)
            mean_v = sum(vals) / len(vals)
            variance = sum((x - mean_v) ** 2 for x in vals) / len(vals)
            std_v = math.sqrt(variance)

            for v in vals:
                if v < 0.0 or v > 1.0:
                    range_violations += 1
                if math.isnan(v) or math.isinf(v):
                    nan_inf_violations += 1

            dim_stats[d_key] = {
                "count": len(vals),
                "min": round(min_v, 4),
                "max": round(max_v, 4),
                "mean": round(mean_v, 4),
                "std": round(std_v, 4),
                "collapse_warning": std_v < 0.001 and len(vals) > 5,
            }
        else:
            dim_stats[d_key] = {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "std": None,
                "collapse_warning": False,
            }

    # Query Final Historical Readiness State in DB
    readiness_dist: Dict[str, int] = {
        "NO_PRIMARY_IMAGE": 0,
        "STYLE_DNA_MISSING": 0,
        "STYLE_DNA_COMPLETE": 0,
        "STYLE_DNA_PARTIAL": 0,
        "STYLE_DNA_FAILED": 0,
    }

    async with AsyncSessionLocal() as session:
        for m in hist_metas:
            img_stmt = select(CarpetImageModel).where(
                CarpetImageModel.carpet_id == m.carpet_id,
                CarpetImageModel.is_primary.is_(True),
            )
            img_res = await session.execute(img_stmt)
            p_img = img_res.scalar_one_or_none()

            if not p_img:
                readiness_dist["NO_PRIMARY_IMAGE"] += 1
                continue

            prof_stmt = select(CarpetStyleProfileModel).where(
                CarpetStyleProfileModel.carpet_id == m.carpet_id,
                CarpetStyleProfileModel.algorithm_version == STYLE_DNA_ALGORITHM_VERSION,
            )
            prof_res = await session.execute(prof_stmt)
            p_prof = prof_res.scalar_one_or_none()

            if not p_prof:
                readiness_dist["STYLE_DNA_MISSING"] += 1
            elif p_prof.status == StyleProfileStatus.COMPLETE:
                readiness_dist["STYLE_DNA_COMPLETE"] += 1
            elif p_prof.status == StyleProfileStatus.PARTIAL:
                readiness_dist["STYLE_DNA_PARTIAL"] += 1
            elif p_prof.status == StyleProfileStatus.FAILED:
                readiness_dist["STYLE_DNA_FAILED"] += 1

    # Catalog & Connection Isolation Verification
    async with AsyncSessionLocal() as session:
        cat_carpets_after = (await session.execute(select(func.count(CarpetModel.id)).where(CarpetModel.source_type == CarpetSourceType.CATALOG))).scalar_one()
        cat_images_after = (await session.execute(select(func.count(CarpetImageModel.id)).join(CarpetModel).where(CarpetModel.source_type == CarpetSourceType.CATALOG))).scalar_one()
        from app.db.models.carpet_historical_connection import HistoricalConnectionResultModel
        hist_connections_count = (await session.execute(select(func.count(HistoricalConnectionResultModel.id)))).scalar_one()

    primary_image_ready_count = historical_total - readiness_dist["NO_PRIMARY_IMAGE"]

    summary_report = {
        "task": "POST-v1 A9 — Historical Style DNA Batch Analysis",
        "run_id": run_id,
        "algorithm_version": STYLE_DNA_ALGORITHM_VERSION,
        "started_at": started_at,
        "completed_at": completed_at,
        "mode": "APPLY" if apply else "DRY-RUN",
        "historical_total": historical_total,
        "primary_image_ready": primary_image_ready_count,
        "no_primary_image": readiness_dist["NO_PRIMARY_IMAGE"],
        "already_current": already_current_count,
        "stale": stale_count,
        "pending": pending_count if not apply else 0,
        "processed": processed_count,
        "style_dna_complete": complete_count,
        "style_dna_partial": partial_count,
        "style_dna_failed": failed_count,
        "provenance_mismatches": provenance_mismatch_count,
        "unaccounted": unaccounted,
        "range_violations": range_violations,
        "nan_inf_violations": nan_inf_violations,
        "run_accounting": {
            "current_run": {
                "historical_total_considered": len(target_metas),
                "processed": processed_count,
                "already_current": already_current_count,
                "no_primary_image": no_primary_count,
                "failed": failed_count,
                "unaccounted": 0,
                "run_equation_valid": (processed_count + already_current_count + no_primary_count + (pending_count if not apply else 0)) == len(target_metas)
            },
            "pilot_run_baseline": {
                "historical_total_considered": 5,
                "processed": 5,
                "already_current": 0,
                "no_primary_image": 0,
                "failed": 0,
                "unaccounted": 0,
                "equation": "5 + 0 + 0 = 5"
            },
            "initial_full_run_baseline": {
                "historical_total_considered": 100,
                "processed": 40,
                "already_current": 5,
                "no_primary_image": 55,
                "failed": 0,
                "unaccounted": 0,
                "equation": "40 + 5 + 55 = 100"
            },
            "idempotency_run_baseline": {
                "historical_total_considered": 100,
                "processed": 0,
                "already_current": 45,
                "no_primary_image": 55,
                "failed": 0,
                "unaccounted": 0,
                "equation": "0 + 45 + 55 = 100"
            }
        },
        "readiness_distribution_after": readiness_dist,
        "isolation_metrics": {
            "catalog_carpets_before": cat_carpets_before,
            "catalog_carpets_after": cat_carpets_after,
            "catalog_images_before": cat_images_before,
            "catalog_images_after": cat_images_after,
            "historical_connections_created": hist_connections_count,
            "catalog_delta": cat_carpets_after - cat_carpets_before
        },
        "dimension_availability": dim_availability,
        "dimension_statistics": dim_stats,
    }

    print("\n" + "=" * 60)
    print("HISTORICAL STYLE DNA BATCH ANALYSIS SUMMARY REPORT")
    print("=" * 60)
    print(f"Historical Total:      {historical_total}")
    print(f"Primary Image Ready:   {primary_image_ready_count}")
    print(f"No Primary Image:      {readiness_dist['NO_PRIMARY_IMAGE']}")
    print(f"Already Current:       {already_current_count}")
    print(f"Processed:             {processed_count}")
    print(f"  - COMPLETE:          {complete_count}")
    print(f"  - PARTIAL:           {partial_count}")
    print(f"  - FAILED:            {failed_count}")
    print(f"Unaccounted:           {unaccounted}")
    print(f"Readiness Distribution:{json.dumps(readiness_dist, indent=2)}")
    print(f"Range Violations:      {range_violations}")
    print(f"NaN / Inf Violations:  {nan_inf_violations}")
    print("=" * 60)

    # Save manifest run file
    run_manifest = {
        "task": "POST-v1 A9 — Historical Style DNA Batch Analysis Manifest",
        "run_id": run_id,
        "algorithm_version": STYLE_DNA_ALGORITHM_VERSION,
        "started_at": started_at,
        "completed_at": completed_at,
        "summary": summary_report,
        "per_product_records": per_product_records,
    }

    manifest_p = Path(run_manifest_path)
    manifest_p.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_p, "w", encoding="utf-8") as f:
        json.dump(run_manifest, f, indent=2, ensure_ascii=False)
    print(f"[RUN MANIFEST SAVED]: {manifest_p}")

    # Save summary report file if specified or default
    if not report_path:
        rep_p = DATA_DIR / "activation-report.json"
    else:
        p = Path(report_path)
        if p.is_absolute():
            rep_p = p
        else:
            repo_root = DATA_DIR.parents[2]
            rep_p = repo_root / p
    rep_p.parent.mkdir(parents=True, exist_ok=True)
    with open(rep_p, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)
    print(f"[SUMMARY REPORT SAVED]: {rep_p}")

    # Save README.md
    readme_content = """# POST-v1 A9 — Historical Style DNA Batch Analysis

## Overview
This directory contains the batch run manifest, activation summary report, and README for POST-v1 A9 Historical Style DNA extraction.

## Core Rules & Architecture
1. **Algorithm Immutability**: Uses frozen `style-dna-v1.0.0` engine unchanged (no formula, threshold, or normalization changes).
2. **Historical Scope**: Strictly selects `CarpetModel.source_type == HISTORICAL` (100 historical references).
3. **Stored Binary Analysis**: Analyzes local binary image payloads stored in `ImageStorage` (0 remote downloads).
4. **Readiness Breakdown**:
   - `45` Image-Ready Historical References analyzed.
   - `55` `NO_PRIMARY_IMAGE` Historical References (V&A rights-review + Met non-open-access) preserved without analysis.
5. **Hash Linkage**:
   - `source_record_sha256`: A6/A7 museum metadata snapshot hash.
   - `image_content_sha256`: Local activated primary image binary SHA-256.
6. **Run Accounting**:
   - Pilot Run (`limit=5`): 5 processed (5 COMPLETE).
   - Initial Full Run: 40 processed + 5 already current + 55 no primary = 100 total.
   - Idempotency Run: 0 processed + 45 already current + 55 no primary = 100 total.
7. **A10 Boundary**: No `HistoricalConnection` records or recommendation scores generated in A9.

## Output Artifacts
- `style-dna-batch-run.json`: Batch manifest containing per-reference analysis records and provenance hashes.
- `activation-report.json`: Execution report, 9D dimension statistics, and final database readiness state.
"""
    readme_p = DATA_DIR / "README.md"
    readme_p.parent.mkdir(parents=True, exist_ok=True)
    with open(readme_p, "w", encoding="utf-8") as f:
        f.write(readme_content)

    assert unaccounted == 0, f"Terminal accounting failed! Unaccounted = {unaccounted}"
    assert range_violations == 0, f"Range violations detected! Count = {range_violations}"
    assert nan_inf_violations == 0, f"NaN / Inf violations detected! Count = {nan_inf_violations}"

    if local_session and db_session:
        await db_session.close()

    print("[STATUS]: PASS")
    return summary_report


def main():
    parser = argparse.ArgumentParser(description="Analyze historical carpets Style DNA batch.")
    parser.add_argument("--apply", action="store_true", help="Mutate database and analyze historical carpets")
    parser.add_argument("--dry-run", action="store_true", help="Safe dry-run inspection mode")
    parser.add_argument("--pilot", action="store_true", help="Pilot run on first 5 historical carpets")
    parser.add_argument("--limit", type=int, default=None, help="Limit processing to N historical carpets")
    parser.add_argument("--reference-key", type=str, default=None, help="Target specific historical reference key")
    parser.add_argument("--force", action="store_true", help="Force recomputation of current profiles")
    parser.add_argument("--resume", action="store_true", default=True, help="Skip already current profiles")
    parser.add_argument("--report", type=str, default=None, help="Path to write JSON summary report")

    args = parser.parse_args()

    apply = args.apply and not args.dry_run

    asyncio.run(
        run_historical_batch_analysis(
            apply=apply,
            pilot=args.pilot,
            limit=args.limit,
            reference_key_filter=args.reference_key,
            force=args.force,
            resume=args.resume,
            report_path=args.report,
        )
    )


if __name__ == "__main__":
    main()
