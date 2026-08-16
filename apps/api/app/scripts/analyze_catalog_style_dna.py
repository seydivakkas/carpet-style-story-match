"""CLI script for batch Style DNA analysis of catalog products v1.

Usage:
  # Dry-run inspection
  python -m app.scripts.analyze_catalog_style_dna --dry-run

  # Pilot run on 5 products
  python -m app.scripts.analyze_catalog_style_dna --pilot --apply --report data/activation/merinos/style-dna-pilot-report.json

  # Full catalog batch analysis
  python -m app.scripts.analyze_catalog_style_dna --apply --resume --report data/activation/merinos/style-dna-batch-report.json
"""

import argparse
import asyncio
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    CarpetStyleDimensionModel,
    StyleProfileStatus,
    StyleDimensionStatus,
)
from app.domain.carpets.exceptions import CarpetNotFoundError
from app.domain.styledna.engine import STYLE_DNA_ALGORITHM_VERSION
from app.domain.styledna.service import StyleDNAService
from app.domain.styledna.exceptions import (
    StyleDNAInputUnavailableError,
    StyleDNAAnalysisFailedError,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_batch_analysis(
    apply: bool = False,
    pilot: bool = False,
    limit: Optional[int] = None,
    sku_filter: Optional[str] = None,
    force: bool = False,
    resume: bool = True,
    report_path: Optional[str] = None,
    run_manifest_path: str = "data/activation/merinos/style-dna-batch-run.json",
) -> Dict[str, Any]:
    run_id = f"run-{int(time.time())}"
    started_at = utc_now_iso()

    if pilot and limit is None:
        limit = 5

    async with AsyncSessionLocal() as session:
        # 1. Manufacturer Audit & Catalog Query
        stmt = (
            select(CarpetModel)
            .where(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                CarpetModel.is_active.is_(True),
            )
            .order_by(
                CarpetModel.manufacturer.asc().nulls_last(),
                CarpetModel.collection.asc().nulls_last(),
                CarpetModel.sku.asc(),
            )
        )
        if sku_filter:
            stmt = stmt.where(CarpetModel.sku == sku_filter)

        res = await session.execute(stmt)
        carpets = list(res.scalars().all())

    # 2. Precompute primary image availability for all catalog carpets
    no_primary_carpet_ids = set()
    async with AsyncSessionLocal() as session:
        for c in carpets:
            img_stmt = select(CarpetImageModel).where(
                CarpetImageModel.carpet_id == c.id,
                CarpetImageModel.is_primary.is_(True),
            )
            img_res = await session.execute(img_stmt)
            p_img = img_res.scalar_one_or_none()
            if not p_img:
                no_primary_carpet_ids.add(c.id)

    no_primary_count = len(no_primary_carpet_ids)
    catalog_total = len(carpets)
    eligible_total = catalog_total - no_primary_count

    # Count by manufacturer
    mfg_counts: Dict[str, int] = {}
    for c in carpets:
        mfg = c.manufacturer or "UNKNOWN"
        mfg_counts[mfg] = mfg_counts.get(mfg, 0) + 1

    print("=" * 60)
    print("CATALOG STYLE DNA BATCH ANALYSIS v1")
    print(f"Run ID:            {run_id}")
    print(f"Algorithm Version: {STYLE_DNA_ALGORITHM_VERSION}")
    print(f"Mode:              {'APPLY (MUTATING)' if apply else 'DRY-RUN (SAFE)'}")
    print(f"Catalog Total:     {catalog_total}")
    print(f"Manufacturers:     {json.dumps(mfg_counts)}")
    print("=" * 60)

    # Apply limit if specified
    if limit is not None:
        target_carpets = carpets[:limit]
    else:
        target_carpets = carpets

    per_product_records: List[Dict[str, Any]] = []

    already_current_count = 0
    processed_count = 0
    complete_count = 0
    partial_count = 0
    failed_count = 0
    stale_count = 0
    pending_count = 0

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

    # Dimension telemetry tracking
    dim_availability: Dict[str, Dict[str, int]] = {
        label: {"AVAILABLE": 0, "LOW_CONFIDENCE": 0, "NOT_AVAILABLE": 0, "FAILED": 0}
        for label in DIM_KEY_MAP.values()
    }
    dim_values_list: Dict[str, List[float]] = {label: [] for label in DIM_KEY_MAP.values()}

    for idx, carpet in enumerate(target_carpets, 1):
        carpet_id = carpet.id
        sku = carpet.sku or f"ID-{carpet.id}"

        # Fetch primary image and current profile for this carpet
        async with AsyncSessionLocal() as session:
            img_stmt = select(CarpetImageModel).where(
                CarpetImageModel.carpet_id == carpet_id,
                CarpetImageModel.is_primary.is_(True),
            )
            img_res = await session.execute(img_stmt)
            primary_img = img_res.scalar_one_or_none()

            prof_stmt = (
                select(CarpetStyleProfileModel)
                .options(selectinload(CarpetStyleProfileModel.dimensions))
                .where(
                    CarpetStyleProfileModel.carpet_id == carpet_id,
                    CarpetStyleProfileModel.algorithm_version == STYLE_DNA_ALGORITHM_VERSION,
                )
            )
            prof_res = await session.execute(prof_stmt)
            existing_prof = prof_res.scalar_one_or_none()

        if not primary_img:
            per_product_records.append({
                "sku": sku,
                "carpet_id": str(carpet_id),
                "primary_image_id": None,
                "image_sha256": None,
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

        # Check idempotency / stale status
        is_already_current = False
        if existing_prof and not force:
            if str(existing_prof.image_id) == str(primary_img.id) and existing_prof.analysis_input_sha256 == primary_img.sha256:
                is_already_current = True
            else:
                stale_count += 1

        if is_already_current and resume:
            already_current_count += 1
            # Record telemetry from existing profile
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
                "sku": sku,
                "carpet_id": str(carpet_id),
                "primary_image_id": str(primary_img.id),
                "image_sha256": primary_img.sha256,
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
            # Dry-run mode: do not execute or persist
            per_product_records.append({
                "sku": sku,
                "carpet_id": str(carpet_id),
                "primary_image_id": str(primary_img.id),
                "image_sha256": primary_img.sha256,
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
            async with AsyncSessionLocal() as session:
                service = StyleDNAService(session)
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
            print(f"[ERROR processing SKU {sku}]: {e}")

        t1 = time.time()
        dur_ms = int((t1 - t0) * 1000)

        per_product_records.append({
            "sku": sku,
            "carpet_id": str(carpet_id),
            "primary_image_id": str(primary_img.id),
            "image_sha256": primary_img.sha256,
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

        if idx % 20 == 0 or idx == len(target_carpets):
            print(f"Processed {idx}/{len(target_carpets)} products... (COMPLETE: {complete_count}, PARTIAL: {partial_count}, FAILED: {failed_count})")

    completed_at = utc_now_iso()

    # 2. Terminal Accounting & Audits
    eligible_total = catalog_total - no_primary_count

    # Terminal status accounting per catalog item
    target_ids = {c.id for c in target_carpets}
    skipped_carpets = [c for c in carpets if c.id not in target_ids]
    skipped_no_primary = sum(1 for c in skipped_carpets if c.id in no_primary_carpet_ids)
    skipped_eligible = len(skipped_carpets) - skipped_no_primary

    accounted_count = (
        no_primary_count
        + complete_count
        + partial_count
        + failed_count
        + (already_current_count if not apply else 0)
        + (pending_count if not apply else 0)
        + skipped_eligible
    )
    unaccounted = catalog_total - accounted_count

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
                "collapse_warning": std_v < 0.001 and len(vals) > 10,
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

    # Query Final Catalog Readiness State
    readiness_dist: Dict[str, int] = {
        "NO_PRIMARY_IMAGE": 0,
        "STYLE_DNA_MISSING": 0,
        "STYLE_DNA_COMPLETE": 0,
        "STYLE_DNA_PARTIAL": 0,
        "STYLE_DNA_FAILED": 0,
    }

    async with AsyncSessionLocal() as session:
        for c in carpets:
            img_stmt = select(CarpetImageModel).where(
                CarpetImageModel.carpet_id == c.id,
                CarpetImageModel.is_primary.is_(True),
            )
            img_res = await session.execute(img_stmt)
            p_img = img_res.scalar_one_or_none()

            if not p_img:
                readiness_dist["NO_PRIMARY_IMAGE"] += 1
                continue

            prof_stmt = select(CarpetStyleProfileModel).where(
                CarpetStyleProfileModel.carpet_id == c.id,
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

    summary_report = {
        "run_id": run_id,
        "algorithm_version": STYLE_DNA_ALGORITHM_VERSION,
        "started_at": started_at,
        "completed_at": completed_at,
        "mode": "APPLY" if apply else "DRY-RUN",
        "catalog_total": catalog_total,
        "manufacturer_distribution": mfg_counts,
        "eligible_total": eligible_total,
        "no_primary_image": no_primary_count,
        "already_current": already_current_count,
        "stale": stale_count,
        "pending": pending_count if not apply else 0,
        "processed": processed_count,
        "style_dna_complete": complete_count,
        "style_dna_partial": partial_count,
        "style_dna_failed": failed_count,
        "unaccounted": unaccounted,
        "range_violations": range_violations,
        "nan_inf_violations": nan_inf_violations,
        "readiness_distribution_after": readiness_dist,
        "dimension_availability": dim_availability,
        "dimension_statistics": dim_stats,
    }

    print("\n" + "=" * 60)
    print("STYLE DNA BATCH ANALYSIS SUMMARY REPORT")
    print("=" * 60)
    print(f"Catalog Total:         {catalog_total}")
    print(f"Eligible (Image-Ready):{eligible_total}")
    print(f"No Primary Image:      {no_primary_count}")
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
        json.dump(run_manifest, f, indent=2)
    print(f"[RUN MANIFEST SAVED]: {manifest_p}")

    # Save report file if specified
    if report_path:
        rep_p = Path(report_path)
        rep_p.parent.mkdir(parents=True, exist_ok=True)
        with open(rep_p, "w", encoding="utf-8") as f:
            json.dump(summary_report, f, indent=2)
        print(f"[SUMMARY REPORT SAVED]: {rep_p}")

    assert unaccounted == 0, f"Terminal accounting failed! Unaccounted = {unaccounted}"
    assert range_violations == 0, f"Range violations detected! Count = {range_violations}"
    assert nan_inf_violations == 0, f"NaN / Inf violations detected! Count = {nan_inf_violations}"

    print("[STATUS]: PASS")
    return summary_report


def main():
    parser = argparse.ArgumentParser(description="Analyze catalog products Style DNA batch.")
    parser.add_argument("--apply", action="store_true", help="Mutate database and analyze products")
    parser.add_argument("--dry-run", action="store_true", help="Safe dry-run inspection mode")
    parser.add_argument("--pilot", action="store_true", help="Pilot run on first 5 products")
    parser.add_argument("--limit", type=int, default=None, help="Limit processing to N products")
    parser.add_argument("--sku", type=str, default=None, help="Target specific SKU")
    parser.add_argument("--force", action="store_true", help="Force recomputation of current profiles")
    parser.add_argument("--resume", action="store_true", default=True, help="Skip already current profiles")
    parser.add_argument("--report", type=str, default=None, help="Path to write JSON summary report")

    args = parser.parse_args()

    apply = args.apply and not args.dry_run

    asyncio.run(
        run_batch_analysis(
            apply=apply,
            pilot=args.pilot,
            limit=args.limit,
            sku_filter=args.sku,
            force=args.force,
            resume=args.resume,
            report_path=args.report,
        )
    )


if __name__ == "__main__":
    main()
