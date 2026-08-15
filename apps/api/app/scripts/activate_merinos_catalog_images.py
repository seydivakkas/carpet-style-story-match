"""Offline activation utility for Merinos catalog product images."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import sys
import uuid
import urllib.parse
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import app.db.models
from app.db.session import AsyncSessionLocal
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.domain.carpets.repository import CarpetRepository
from app.domain.carpets.service import CarpetService
from app.domain.images.exceptions import ImageDuplicateError
from app.domain.images.repository import CarpetImageRepository
from app.domain.images.service import CarpetImageService
from app.domain.images.storage import LocalImageStorage
from app.domain.images.validation import ImageValidationService
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

    # --- AUTHORIZED_INTERNAL MODE INGESTION ---
    print("\n[2/3] Executing AUTHORIZED_INTERNAL image acquisition & database ingestion...")
    activated_count = 0
    already_active_count = 0
    invalid_count = 0
    download_failed_count = 0
    storage_failed_count = 0
    activation_records = []

    async def _process_with_session(sess: AsyncSession):
        nonlocal activated_count, already_active_count, invalid_count, download_failed_count, storage_failed_count, image_url_missing_count
        carpet_repo = CarpetRepository(sess)
        carpet_service = CarpetService(carpet_repo)
        image_repo = CarpetImageRepository(sess)
        storage = LocalImageStorage()
        validator = ImageValidationService()
        image_service = CarpetImageService(carpet_service, image_repo, storage, validator)

        for idx, p in enumerate(products, 1):
            sku = p.get("sku", "").strip()
            prod_url = p.get("source_url", "")
            img_url = p.get("primary_image_url")

            print(f"  [{idx}/{len(products)}] Processing SKU '{sku}'...")

            if not img_url:
                print(f"    Notice: No primary image URL for SKU '{sku}'")
                image_url_missing_count += 1
                activation_records.append({
                    "sku": sku,
                    "product_url": prod_url,
                    "source_image_url": None,
                    "rights_mode": rights_mode,
                    "status": "IMAGE_NOT_FOUND",
                    "activated_at": None,
                })
                continue

            # Lookup Carpet record by SKU
            carpet = await carpet_repo.get_by_sku(sku)
            if not carpet:
                print(f"    WARNING: Carpet model with SKU '{sku}' not found in DB", file=sys.stderr)
                activation_records.append({
                    "sku": sku,
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "SOURCE_PRODUCT_UNAVAILABLE",
                    "activated_at": None,
                })
                continue

            # Check if primary image already exists
            existing_images = await image_repo.list_by_carpet_id(carpet.id)
            has_primary = any(img.is_primary for img in existing_images)
            if has_primary and not replace_primary:
                print(f"    Notice: Carpet SKU '{sku}' already has a primary image. Skipping.")
                already_active_count += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "ALREADY_ACTIVE",
                    "activated_at": datetime.now(timezone.utc).isoformat(),
                })
                continue

            # Download official image bytes safely
            try:
                raw_bytes, content_type = download_image_bytes(img_url, timeout=15, delay_sec=0.5)
            except (InvalidHostError, InvalidSchemeError, RedirectHostError) as e:
                print(f"    Security rejection for image URL '{img_url}': {e}", file=sys.stderr)
                download_failed_count += 1
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
            except Exception as e:
                print(f"    Validation or storage ingestion failed for SKU '{sku}': {e}", file=sys.stderr)
                storage_failed_count += 1
                activation_records.append({
                    "sku": sku,
                    "carpet_id": str(carpet.id),
                    "product_url": prod_url,
                    "source_image_url": img_url,
                    "rights_mode": rights_mode,
                    "status": "INVALID_IMAGE",
                    "activated_at": None,
                })

    if session is not None:
        await _process_with_session(session)
    else:
        async with AsyncSessionLocal() as sess:
            await _process_with_session(sess)

    total_prods = len(products)
    total_active = activated_count + already_active_count
    act_rate = (total_active / total_prods * 100.0) if total_prods > 0 else 0.0

    report = {
        "rights_mode": rights_mode,
        "dry_run": dry_run,
        "products_total": total_prods,
        "image_url_found": image_url_found_count,
        "image_url_missing": image_url_missing_count,
        "activated": activated_count,
        "already_active": already_active_count,
        "invalid": invalid_count,
        "download_failed": download_failed_count,
        "storage_failed": storage_failed_count,
        "primary_image_count": total_active,
        "activation_rate": round(act_rate, 2),
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
    print(f"\n[SUMMARY] Total: {total_prods}, Activated: {activated_count}, Already Active: {already_active_count}, Rate: {round(act_rate, 2)}%")


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
