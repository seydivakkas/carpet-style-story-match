"""Script to build motif curation review queue and process curation decisions for POST-v1 A5."""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
IMAGE_ACTIVATION_PATH = PROJECT_ROOT / "data" / "activation" / "merinos" / "merinos-image-activation.json"
CURATION_DIR = PROJECT_ROOT / "data" / "activation" / "merinos" / "motif_curation"
REVIEW_QUEUE_PATH = CURATION_DIR / "review-queue.json"
REVIEW_RESULTS_PATH = CURATION_DIR / "review-results.json"
CURATION_DATASET_PATH = CURATION_DIR / "carpet-motif-story-curation.json"


def build_review_queue():
    """Generate review-queue.json from merinos-image-activation.json."""
    if not IMAGE_ACTIVATION_PATH.exists():
        print(f"Error: {IMAGE_ACTIVATION_PATH} missing", file=sys.stderr)
        sys.exit(1)

    with open(IMAGE_ACTIVATION_PATH, "r", encoding="utf-8") as f:
        activation_data = json.load(f)

    records = activation_data.get("activated_records", [])

    existing_results = {}
    if REVIEW_RESULTS_PATH.exists():
        with open(REVIEW_RESULTS_PATH, "r", encoding="utf-8") as f:
            res_data = json.load(f)
            existing_results = {r["sku"]: r for r in res_data.get("reviews", [])}

    queue_items = []
    for rec in records:
        sku = rec["sku"]
        rev_status = "PENDING"
        if sku in existing_results:
            rev_status = existing_results[sku].get("review_status", "REVIEWED")

        queue_items.append({
            "sku": sku,
            "carpet_id": rec.get("carpet_id"),
            "collection": rec.get("collection", sku.split()[0] if " " in sku else "Merinos"),
            "product_name": f"Merinos {sku}",
            "primary_image_id": rec.get("image_id"),
            "image_sha256": rec.get("content_sha256"),
            "image_reference": rec.get("source_image_url"),
            "style_dna_readiness": "STYLE_DNA_COMPLETE" if rec.get("image_id") else "NO_PRIMARY_IMAGE",
            "candidate_decisions": [],
            "review_status": rev_status
        })

    CURATION_DIR.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "queue_version": "carpet-motif-review-v1",
            "total_products": len(queue_items),
            "pending_count": sum(1 for item in queue_items if item["review_status"] == "PENDING"),
            "reviewed_count": sum(1 for item in queue_items if item["review_status"] == "REVIEWED"),
            "skipped_count": sum(1 for item in queue_items if item["review_status"] == "SKIPPED"),
            "items": queue_items
        }, f, ensure_ascii=False, indent=2)

    print(f"[REVIEW QUEUE GENERATED]: {len(queue_items)} items written to {REVIEW_QUEUE_PATH}")


def check_stale_reviews() -> List[Dict[str, Any]]:
    """Detect reviews referencing outdated primary image IDs or SHA256 hashes."""
    if not REVIEW_QUEUE_PATH.exists() or not REVIEW_RESULTS_PATH.exists():
        return []

    with open(REVIEW_QUEUE_PATH, "r", encoding="utf-8") as f:
        queue_data = json.load(f)
        queue_map = {item["sku"]: item for item in queue_data.get("items", [])}

    with open(REVIEW_RESULTS_PATH, "r", encoding="utf-8") as f:
        results_data = json.load(f)
        results = results_data.get("reviews", [])

    stale_reviews = []
    for r in results:
        sku = r["sku"]
        if sku in queue_map:
            q_item = queue_map[sku]
            if (
                r.get("primary_image_id") != q_item["primary_image_id"] or
                r.get("image_sha256") != q_item["image_sha256"]
            ):
                stale_reviews.append({
                    "sku": sku,
                    "reason": "STALE_IMAGE_REVIEW",
                    "recorded_image_id": r.get("primary_image_id"),
                    "current_image_id": q_item["primary_image_id"],
                    "recorded_sha256": r.get("image_sha256"),
                    "current_sha256": q_item["image_sha256"]
                })
    return stale_reviews


def export_curation_dataset():
    """Convert review-results.json into carpet-motif-story-curation.json dataset."""
    if not REVIEW_RESULTS_PATH.exists():
        print(f"Error: {REVIEW_RESULTS_PATH} missing", file=sys.stderr)
        sys.exit(1)

    stale = check_stale_reviews()
    if stale:
        print(f"Warning: {len(stale)} stale reviews detected!", file=sys.stderr)

    with open(REVIEW_RESULTS_PATH, "r", encoding="utf-8") as f:
        results_data = json.load(f)

    stale_skus = {s["sku"] for s in stale}
    carpets = []

    for rev in results_data.get("reviews", []):
        sku = rev["sku"]
        if sku in stale_skus or rev.get("review_status") != "REVIEWED":
            continue

        motifs_input = []
        for m in rev.get("motifs", []):
            if m["decision"] not in ("CONFIRMED", "UNCERTAIN"):
                continue

            ev_type = m["evidence_type"]
            c_note = m.get("note") if ev_type == "CURATOR_CONFIRMED" else None
            u_note = m.get("note") if ev_type == "UNCERTAIN" else None

            # Gather story claim links attached to this motif
            sc_links = []
            if ev_type != "UNCERTAIN":
                for st in rev.get("stories", []):
                    if st.get("motif_key") == m["motif_key"] and st.get("decision") == "ATTACH":
                        sc_links.append({
                            "claim_key": st["claim_key"],
                            "applicability_note": st.get("applicability_note")
                        })

            presence_srcs = []
            if ev_type == "SOURCE_DOCUMENTED":
                for ps in m.get("presence_sources", []):
                    presence_srcs.append({
                        "source_key": ps["source_key"],
                        "locator": ps.get("locator"),
                        "source_note": ps.get("source_note")
                    })

            motifs_input.append({
                "motif_key": m["motif_key"],
                "evidence_type": ev_type,
                "curation_note": c_note,
                "uncertainty_note": u_note,
                "sources": presence_srcs,
                "story_claim_keys": sc_links
            })

        coll = rev.get("collection") or (sku.split()[0] if " " in sku else "Merinos")
        if motifs_input:
            carpets.append({
                "sku": sku,
                "name": f"{coll} {sku}",
                "collection": coll,
                "manufacturer": "Merinos",
                "motifs": motifs_input
            })

    dataset = {
        "schema_version": "carpet-catalog-curation-v1",
        "carpets": carpets
    }

    with open(CURATION_DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"[CURATION DATASET EXPORTED]: {len(carpets)} carpets written to {CURATION_DATASET_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Build and process motif curation workflow for POST-v1 A5.")
    parser.add_argument("--build-queue", action="store_true", help="Generate review-queue.json")
    parser.add_argument("--check-stale", action="store_true", help="Check for stale image reviews")
    parser.add_argument("--export-dataset", action="store_true", help="Export curation JSON dataset")

    args = parser.parse_args()

    if args.build_queue:
        build_review_queue()
    if args.check_stale:
        stale = check_stale_reviews()
        print(f"Stale reviews found: {len(stale)}")
    if args.export_dataset:
        export_curation_dataset()


if __name__ == "__main__":
    main()
