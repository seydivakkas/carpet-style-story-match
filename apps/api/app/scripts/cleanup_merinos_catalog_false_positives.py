"""Deterministic cleanup utility for Merinos catalog false-positive non-product records."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import sys
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import app.db.models
from app.db.session import AsyncSessionLocal
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import CarpetStyleProfileModel
from app.db.models.carpet_story_association import (
    CarpetMotifAssociationModel,
    CarpetStoryAssociationModel,
)
from app.domain.carpet_catalog.merinos_parser import is_non_product_url, is_valid_product_sku


def get_repo_root() -> str:
    """Return the absolute path of the repository root."""
    current_file = os.path.abspath(__file__)
    return os.path.abspath(os.path.join(os.path.dirname(current_file), "..", "..", "..", ".."))


async def run_cleanup_async(
    dry_run: bool,
    apply: bool,
    source_file: str,
    output_report: str,
    session: Optional[AsyncSession] = None,
):
    print("=== MERINOS CATALOG FALSE-POSITIVE CLEANUP ===")
    print(f"  Dry Run: {dry_run}")
    print(f"  Apply: {apply}")
    print(f"  Canonical Source File: {source_file}")

    if not dry_run and not apply:
        print("Error: --apply flag is required to mutate database.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(source_file):
        print(f"Error: Source catalog file not found: {source_file}", file=sys.stderr)
        sys.exit(1)

    with open(source_file, "r", encoding="utf-8") as f:
        source_data = json.load(f)

    canonical_skus = {p.get("sku", "").strip().upper() for p in source_data.get("products", [])}

    async def _process_with_session(sess: AsyncSession):
        # Query all DB catalog carpets
        db_res = await sess.execute(
            select(CarpetModel).where(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                CarpetModel.is_active.is_(True)
            ).order_by(CarpetModel.sku)
        )
        db_carpets = db_res.scalars().all()
        db_catalog_before = len(db_carpets)

        false_positive_candidates = []
        review_required = []

        for c in db_carpets:
            sku_norm = c.sku.strip().upper()
            source_ref = c.source_reference or ""

            # Check eligibility
            is_non_prod_route = is_non_product_url(source_ref)
            is_invalid_sku = not is_valid_product_sku(sku_norm)
            not_in_canonical = sku_norm not in canonical_skus

            if is_non_prod_route or is_invalid_sku or not_in_canonical:
                # Perform dependency audit
                img_cnt = (await sess.execute(
                    select(func.count(CarpetImageModel.id)).where(CarpetImageModel.carpet_id == c.id)
                )).scalar_one()

                profile_cnt = (await sess.execute(
                    select(func.count(CarpetStyleProfileModel.id)).where(CarpetStyleProfileModel.carpet_id == c.id)
                )).scalar_one()

                motif_cnt = (await sess.execute(
                    select(func.count(CarpetMotifAssociationModel.id)).where(CarpetMotifAssociationModel.carpet_id == c.id)
                )).scalar_one()

                rec = {
                    "sku": c.sku,
                    "carpet_id": str(c.id),
                    "source_reference": source_ref,
                    "reason": "BLOG_ARCHIVE_NON_PRODUCT_ROUTE" if is_non_prod_route else "INVALID_SKU_NOT_IN_CANONICAL_SOURCE",
                    "dependent_image_count": img_cnt,
                    "dependent_style_profile_count": profile_cnt,
                    "dependent_motif_association_count": motif_cnt,
                    "deletion_status": "DRY_RUN_ELIGIBLE" if dry_run else "DELETED",
                }

                # Proven false-positive check (non-product route + not in canonical source + 0 dependencies)
                if (is_non_prod_route or is_invalid_sku) and not_in_canonical and img_cnt == 0 and profile_cnt == 0:
                    false_positive_candidates.append((c, rec))
                else:
                    rec["deletion_status"] = "REVIEW_REQUIRED"
                    review_required.append(rec)

        deleted_count = 0
        if apply and not dry_run:
            for carpet, rec in false_positive_candidates:
                await sess.delete(carpet)
                deleted_count += 1
            await sess.commit()
            print(f"\n[APPLIED] Successfully deleted {deleted_count} false-positive catalog records from database.")
        else:
            print(f"\n[DRY-RUN] Found {len(false_positive_candidates)} candidate false-positive records. 0 DB rows deleted.")

        per_record_report = [rec for _, rec in false_positive_candidates] + review_required
        db_catalog_after = db_catalog_before - deleted_count

        report = {
            "rights_mode": "CLEANUP",
            "dry_run": dry_run,
            "applied": apply,
            "db_catalog_before": db_catalog_before,
            "canonical_source_skus": len(canonical_skus),
            "false_positive_candidates": len(false_positive_candidates),
            "deleted": deleted_count,
            "review_required": len(review_required),
            "db_catalog_after": db_catalog_after,
            "per_record": per_record_report,
        }

        os.makedirs(os.path.dirname(os.path.abspath(output_report)), exist_ok=True)
        with open(output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"  Saved catalog cleanup report: {output_report}")
        print(f"\n[SUMMARY] DB Catalog Before: {db_catalog_before}, Deleted: {deleted_count}, DB Catalog After: {db_catalog_after}")

    if session is not None:
        await _process_with_session(session)
    else:
        async with AsyncSessionLocal() as sess:
            await _process_with_session(sess)


def main():
    repo_root = get_repo_root()
    default_source_file = os.path.join(repo_root, "data", "activation", "merinos", "merinos-catalog-source.json")
    default_report = os.path.join(repo_root, "data", "activation", "merinos", "catalog-cleanup-report.json")

    parser = argparse.ArgumentParser(description="Cleanup Merinos catalog false positive non-product records.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform audit without deleting database rows (default)")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Disable dry run mode")
    parser.add_argument("--apply", action="store_true", help="Explicit confirmation flag required to execute database deletion")
    parser.add_argument("--source-file", default=default_source_file, help="Path to merinos-catalog-source.json")
    parser.add_argument("--output-report", default=default_report, help="Path for catalog-cleanup-report.json")

    args = parser.parse_args()

    # Handle --apply setting dry_run to False
    if args.apply:
        args.dry_run = False

    asyncio.run(
        run_cleanup_async(
            dry_run=args.dry_run,
            apply=args.apply,
            source_file=args.source_file,
            output_report=args.output_report,
        )
    )


if __name__ == "__main__":
    main()
