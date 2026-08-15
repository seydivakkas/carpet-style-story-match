"""Offline activation utility for Merinos catalog product images."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import sys
import uuid
import urllib.parse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import app.db.models
from app.db.session import AsyncSessionLocal
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.domain.carpets.repository import CarpetRepository
from app.domain.carpets.service import CarpetService
from app.domain.images.exceptions import ImageDuplicateError, ImageDomainException, ImageStorageFailedError
from app.domain.images.repository import CarpetImageRepository
from app.domain.images.service import CarpetImageService
from app.domain.images.storage import LocalImageStorage
from app.domain.images.validation import ImageValidationService
from app.domain.carpet_catalog.repository import CarpetCatalogRepository
from app.domain.carpet_catalog.merinos_image_downloader import (
    download_image_bytes,
    is_host_allowlisted,
    validate_image_url_host,
    InvalidHostError,
    InvalidSchemeError,
    RedirectHostError,
    ImageOversizeError,
)


def get_repo_root() -> str:
    """Return the absolute path of the repository root."""
    current_file = os.path.abspath(__file__)
    return os.path.abspath(os.path.join(os.path.dirname(current_file), "..", "..", "..", ".."))


async def run_activation_async(
    source_file: str,
    rights_mode: str,
    dry_run: bool,
    apply: bool,
    limit: Optional[int],
    replace_primary: bool,
    output_source_images: str,
    output_activation: str,
    output_report: str,
    session: Optional[AsyncSession] = None,
):
    print("=== MERINOS CATALOG PRODUCT IMAGE ACTIVATION ===")
    print(f"  Rights Mode: {rights_mode}")
    print(f"  Dry Run: {dry_run}")
    print(f"  Apply: {apply}")
    print(f"  Limit: {limit if limit else 'ALL'}")

    if rights_mode not in ("URL_ONLY", "AUTHORIZED_INTERNAL"):
        print(f"Error: Invalid rights_mode '{rights_mode}'. Must be URL_ONLY or AUTHORIZED_INTERNAL.", file=sys.stderr)
        sys.exit(1)

    if rights_mode == "AUTHORIZED_INTERNAL" and not dry_run and not apply:
        print("Error: --apply flag is required for AUTHORIZED_INTERNAL mode to persist images.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(source_file):
        print(f"Error: Source catalog file not found: {source_file}", file=sys.stderr)
        sys.exit(1)

    with open(source_file, "r", encoding="utf-8") as f:
        source_data = json.load(f)

    products = source_data.get("products", [])
    if limit and limit > 0:
        products = products[:limit]

    retrieved_at = datetime.now(timezone.utc).isoformat()

    image_source_records = []
    image_url_found_count = 0
    image_url_missing_count = 0

    print("\n[1/3] Processing image URL candidates and host allowlist...")
    for p in products:
        sku = p.get("sku", "")
        prod_url = p.get("source_url", "")
        primary_img_url = p.get("primary_image_url")

        candidates = []
        if primary_img_url:
            try:
                validate_image_url_host(primary_img_url)
                host = primary_img_url.split("//")[-1].split("/")[0]
                candidates.append({
                    "source_url": primary_img_url,
                    "role": "PRIMARY_CANDIDATE",
                    "source_page_url": prod_url,
                    "discovered_at": retrieved_at,
                    "source_host": host,
                    "valid_host": True,
                })
                image_url_found_count += 1
            except Exception as e:
                print(f"  Notice: Invalid candidate host for SKU '{sku}': {e}")
                image_url_missing_count += 1
        else:
            image_url_missing_count += 1

        image_source_records.append({
            "sku": sku,
            "product_url": prod_url,
            "image_candidates": candidates,
        })

    image_source_dataset = {
        "dataset_type": "merinos-catalog-image-source",
        "retrieved_at": retrieved_at,
        "products": image_source_records,
    }

    # Write merinos-image-source.json
    os.makedirs(os.path.dirname(os.path.abspath(output_source_images)), exist_ok=True)
    with open(output_source_images, "w", encoding="utf-8") as f:
        json.dump(image_source_dataset, f, ensure_ascii=False, indent=2)
    print(f"  Saved image source dataset: {output_source_images}")

    if rights_mode == "URL_ONLY" or dry_run:
        print("\n[URL_ONLY / DRY-RUN MODE COMPLETE]")
        print("  No binary image download performed. 0 CarpetImage DB rows created.")
        
        activation_records = []
        for p in products:
            sku = p.get("sku", "")
            img_url = p.get("primary_image_url")
            activation_records.append({
                "sku": sku,
                "product_url": p.get("source_url", ""),
                "source_image_url": img_url,
                "rights_mode": rights_mode,
                "status": "URL_ONLY" if img_url else "IMAGE_NOT_FOUND",
                "activated_at": None,
            })

        activation_dataset = {
            "dataset_type": "merinos-image-activation-sidecar",
            "rights_mode": rights_mode,
            "dry_run": dry_run,
            "activated_records": activation_records,
        }

        report = {
            "rights_mode": rights_mode,
            "dry_run": dry_run,
            "products_total": len(products),
            "image_url_found": image_url_found_count,
            "image_url_missing": image_url_missing_count,
            "activated": 0,
            "already_active": 0,
            "invalid": 0,
            "download_failed": 0,
            "storage_failed": 0,
            "primary_image_count": 0,
            "activation_rate": 0.0,
        }

        os.makedirs(os.path.dirname(os.path.abspath(output_activation)), exist_ok=True)
        with open(output_activation, "w", encoding="utf-8") as f:
            json.dump(activation_dataset, f, ensure_ascii=False, indent=2)

        os.makedirs(os.path.dirname(os.path.abspath(output_report)), exist_ok=True)
        with open(output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"  Saved activation sidecar: {output_activation}")
        print(f"  Saved image activation report: {output_report}")
        return

    # --- DB CATALOG CARPET RECONCILIATION & ACQUISITION ---
    print("\n[2/3] Reconciling DB catalog population & executing image ingestion...")
    
    async def _process_with_session(sess: AsyncSession):
        carpet_repo = CarpetRepository(sess)
        catalog_repo = CarpetCatalogRepository(sess)
        carpet_service = CarpetService(carpet_repo)
        image_repo = CarpetImageRepository(sess)
        storage = LocalImageStorage()
        validator = ImageValidationService()
        image_service = CarpetImageService(carpet_service, image_repo, storage, validator)

        # Query canonical DB catalog carpets
        db_carpets_res = await sess.execute(
            select(CarpetModel).where(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                CarpetModel.is_active.is_(True)
            ).order_by(CarpetModel.sku)
        )
        db_carpets = db_carpets_res.scalars().all()
        db_carpet_map = {c.sku.strip().upper(): c for c in db_carpets}
        
        # Build lookup from source dataset
        source_map = {p.get("sku", "").strip().upper(): p for p in products}

        # Combine all canonical SKUs (DB catalog SKUs + source products)
        all_skus = sorted(list(set(db_carpet_map.keys()).union(source_map.keys())))
        if limit and limit > 0:
            all_skus = all_skus[:limit]

        activated_count = 0
        already_active_count = 0
        source_product_unavailable_count = 0
        image_not_found_count = 0
        invalid_count = 0
        download_failed_count = 0
        storage_failed_count = 0
        skipped_existing_primary_count = 0
        
        activation_records = []
        readiness_distribution = {
            "NO_PRIMARY_IMAGE": 0,
            "STYLE_DNA_MISSING": 0,
            "STYLE_DNA_FAILED": 0,
            "STYLE_DNA_PARTIAL": 0,
            "STYLE_DNA_COMPLETE": 0,
        }

        for idx, sku in enumerate(all_skus, 1):
            print(f"  [{idx}/{len(all_skus)}] Reconciling SKU '{sku}'...")
            carpet = db_carpet_map.get(sku)
            source_p = source_map.get(sku)

            # Check if SKU is in source dataset
            if not source_p:
                print(f"    Notice: SKU '{sku}' present in DB but unavailable in source dataset (non-product URL).")
                source_product_unavailable_count += 1
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id) if carpet else None,
                    "product_url": carpet.source_reference if carpet else "",
                    "source_image_url": None,
                    "rights_mode": rights_mode,
                    "status": "SOURCE_PRODUCT_UNAVAILABLE",
                    "activated_at": None,
                })
                continue

            prod_url = source_p.get("source_url", "")
            img_url = source_p.get("primary_image_url")

            if not carpet:
                print(f"    WARNING: SKU '{sku}' in source dataset but not found in DB.", file=sys.stderr)
                source_product_unavailable_count += 1
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": None,
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "SOURCE_PRODUCT_UNAVAILABLE",
                    "activated_at": None,
                })
                continue

            # Check existing DB primary image
            existing_primary = await catalog_repo.get_primary_image(carpet.id)
            if existing_primary and not replace_primary:
                print(f"    Notice: Carpet SKU '{sku}' already has primary image (ID={existing_primary.id}).")
                already_active_count += 1
                readiness_distribution["STYLE_DNA_MISSING"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "image_id": str(existing_primary.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "ACTIVATED",
                    "content_sha256": existing_primary.sha256,
                    "image_width": existing_primary.width_px,
                    "image_height": existing_primary.height_px,
                    "content_type": existing_primary.content_type,
                    "activated_at": existing_primary.created_at.isoformat(),
                })
                continue

            if not img_url:
                print(f"    Notice: No primary image URL available for SKU '{sku}'.")
                image_not_found_count += 1
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": None,
                    "rights_mode": rights_mode,
                    "status": "IMAGE_NOT_FOUND",
                    "activated_at": None,
                })
                continue

            if rights_mode == "URL_ONLY" or dry_run:
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "URL_ONLY",
                    "activated_at": None,
                })
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                continue

            # Download official image bytes safely
            try:
                raw_bytes, content_type = download_image_bytes(img_url, timeout=15, delay_sec=0.5)
            except (InvalidHostError, InvalidSchemeError, RedirectHostError) as e:
                print(f"    Security rejection for image URL '{img_url}': {e}", file=sys.stderr)
                download_failed_count += 1
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "SECURITY_REJECTED",
                    "activated_at": None,
                })
                continue
            except ImageOversizeError as e:
                print(f"    Oversize image for SKU '{sku}': {e}", file=sys.stderr)
                invalid_count += 1
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "OVERSIZE_REJECTED",
                    "activated_at": None,
                })
                continue
            except Exception as e:
                print(f"    Download failed for SKU '{sku}': {e}", file=sys.stderr)
                download_failed_count += 1
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "DOWNLOAD_FAILED",
                    "activated_at": None,
                })
                continue

            # Upload & ingest via CarpetImageService
            try:
                filename = os.path.basename(urllib.parse.urlparse(img_url).path) or f"{sku}.jpg"
                image_model = await image_service.upload_carpet_image(
                    carpet_id=carpet.id,
                    original_filename=filename,
                    content_type=content_type,
                    file_bytes=raw_bytes,
                )

                activated_count += 1
                readiness_distribution["STYLE_DNA_MISSING"] += 1
                print(f"    [SUCCESS] Activated primary image (ID={image_model.id}, {image_model.width_px}x{image_model.height_px}px) for SKU '{sku}'")

                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "image_id": str(image_model.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "ACTIVATED",
                    "content_sha256": image_model.sha256,
                    "image_width": image_model.width_px,
                    "image_height": image_model.height_px,
                    "content_type": image_model.content_type,
                    "activated_at": datetime.now(timezone.utc).isoformat(),
                })
            except ImageDuplicateError:
                already_active_count += 1
                readiness_distribution["STYLE_DNA_MISSING"] += 1
                print(f"    Notice: Image for SKU '{sku}' already active in DB.")
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "ALREADY_ACTIVE",
                    "activated_at": datetime.now(timezone.utc).isoformat(),
                })
            except ImageStorageFailedError as e:
                print(f"    Storage persistence failed for SKU '{sku}': {e}", file=sys.stderr)
                storage_failed_count += 1
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "STORAGE_FAILED",
                    "activated_at": None,
                })
            except ImageDomainException as e:
                print(f"    Image validation failed for SKU '{sku}': {e}", file=sys.stderr)
                invalid_count += 1
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "INVALID_IMAGE",
                    "activated_at": None,
                })
            except Exception as e:
                print(f"    Unexpected error for SKU '{sku}': {e}", file=sys.stderr)
                storage_failed_count += 1
                readiness_distribution["NO_PRIMARY_IMAGE"] += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "STORAGE_FAILED",
                    "activated_at": None,
                })

        total_catalog = len(all_skus)
        total_activated_or_active = activated_count + already_active_count
        
        # Calculate terminal totals & unaccounted invariant
        terminal_total = (
            total_activated_or_active
            + source_product_unavailable_count
            + image_not_found_count
            + invalid_count
            + download_failed_count
            + storage_failed_count
            + skipped_existing_primary_count
        )
        unaccounted = total_catalog - terminal_total

        whole_cat_rate = (total_activated_or_active / total_catalog * 100.0) if total_catalog > 0 else 0.0
        source_avail_rate = (total_activated_or_active / len(products) * 100.0) if len(products) > 0 else 0.0

        report = {
            "rights_mode": rights_mode,
            "dry_run": dry_run,
            "authorization_assumed": False,
            "catalog_total": total_catalog,
            "source_records_total": len(products),
            "processed_total": len(all_skus),
            "image_url_found": image_url_found_count,
            "image_url_missing": total_catalog - image_url_found_count,
            "activated": activated_count,
            "already_active": already_active_count,
            "source_product_unavailable": source_product_unavailable_count,
            "image_not_found": image_not_found_count,
            "invalid_image": invalid_count,
            "download_failed": download_failed_count,
            "storage_failed": storage_failed_count,
            "skipped_existing_primary": skipped_existing_primary_count,
            "terminal_status_total": terminal_total,
            "unaccounted": unaccounted,
            "primary_image_count": total_activated_or_active,
            "without_primary_image_count": total_catalog - total_activated_or_active,
            "activation_rate_whole_catalog": round(whole_cat_rate, 4),
            "activation_rate_source_available": round(source_avail_rate, 4),
            "readiness_distribution": readiness_distribution,
            "style_dna_profiles_created": 0,
        }

        activation_dataset = {
            "dataset_type": "merinos-image-activation-sidecar",
            "rights_mode": rights_mode,
            "dry_run": dry_run,
            "activated_records": activation_records,
        }

        print("\n[3/3] Saving activation reports...")
        os.makedirs(os.path.dirname(os.path.abspath(output_activation)), exist_ok=True)
        with open(output_activation, "w", encoding="utf-8") as f:
            json.dump(activation_dataset, f, ensure_ascii=False, indent=2)

        os.makedirs(os.path.dirname(os.path.abspath(output_report)), exist_ok=True)
        with open(output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"  Activation sidecar saved: {output_activation}")
        print(f"  Activation report saved: {output_report}")
        print(f"\n[SUMMARY] Catalog Total: {total_catalog}, Primary Active: {total_activated_or_active}, Unaccounted: {unaccounted}, Rate: {round(whole_cat_rate, 2)}%")

    if session is not None:
        await _process_with_session(session)
    else:
        async with AsyncSessionLocal() as sess:
            await _process_with_session(sess)


def main():
    repo_root = get_repo_root()
    default_source_file = os.path.join(repo_root, "data", "activation", "merinos", "merinos-catalog-source.json")
    default_source_images = os.path.join(repo_root, "data", "activation", "merinos", "merinos-image-source.json")
    default_activation = os.path.join(repo_root, "data", "activation", "merinos", "merinos-image-activation.json")
    default_report = os.path.join(repo_root, "data", "activation", "merinos", "image-activation-report.json")

    parser = argparse.ArgumentParser(description="Activate Merinos catalog product images.")
    parser.add_argument("source_file", nargs="?", default=default_source_file, help="Path to merinos-catalog-source.json")
    parser.add_argument("--rights-mode", default="URL_ONLY", choices=["URL_ONLY", "AUTHORIZED_INTERNAL"], help="Rights mode for image acquisition (default: URL_ONLY)")
    parser.add_argument("--dry-run", action="store_true", help="Perform validation without downloading or persisting images")
    parser.add_argument("--apply", action="store_true", help="Explicit confirmation flag required for AUTHORIZED_INTERNAL DB mutation")
    parser.add_argument("--limit", type=int, help="Limit number of products to process (for pilot testing)")
    parser.add_argument("--replace-primary", action="store_true", help="Replace existing primary image if present")
    parser.add_argument("--output-source-images", default=default_source_images, help="Path for image source dataset")
    parser.add_argument("--output-activation", default=default_activation, help="Path for activation sidecar")
    parser.add_argument("--output-report", default=default_report, help="Path for activation report")

    args = parser.parse_args()

    asyncio.run(
        run_activation_async(
            source_file=args.source_file,
            rights_mode=args.rights_mode,
            dry_run=args.dry_run,
            apply=args.apply,
            limit=args.limit,
            replace_primary=args.replace_primary,
            output_source_images=args.output_source_images,
            output_activation=args.output_activation,
            output_report=args.output_report,
        )
    )


if __name__ == "__main__":
    main()
