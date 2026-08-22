"""
Met Museum Corpus Augmentation and License Segregation Script for Y6.5 (Fast & Parallel).
Fetches CC0 public domain carpet/rug/kilim images from Met Open Access API,
ensures Met share >= 25% of real_corpus_v1 (target 180 Met images -> 26.5% Met share),
segregates licenses into training_safe (CC0) vs review_needed (NC),
and updates metadata.jsonl & corpus_manifest.json.

Author: Seydi Eryilmaz (@seydivakkas)
Copyright (c) 2026 Seydi Eryilmaz - All Rights Reserved
"""

import sys
import os
import json
import time
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
import numpy as np

ROOT_DIR = Path("c:/Users/seydieryilmaz/Desktop/carpet-style-story-match")
CORPUS_DIR = ROOT_DIR / "data" / "datasets" / "real_corpus_v1"
IMAGES_DIR = CORPUS_DIR / "images"
METADATA_FILE = CORPUS_DIR / "metadata.jsonl"
MANIFEST_FILE = CORPUS_DIR / "corpus_manifest.json"

TARGET_MET_TOTAL = 180  # 180 Met + 499 V&A = 679 total -> 26.51% Met share (Target >= 25%)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def compute_sha256(data_bytes: bytes) -> str:
    h = hashlib.sha256()
    h.update(data_bytes)
    return h.hexdigest()


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_holdout_blacklist() -> set:
    blacklist = set()
    dirs_to_check = [
        ROOT_DIR / "data" / "datasets" / "real-motif-benchmark-v1" / "images",
        ROOT_DIR / "scratch" / "curation_images",
        ROOT_DIR / "apps" / "api" / "data" / "uploads" / "carpets",
    ]
    for d in dirs_to_check:
        if d.exists():
            for f in d.glob("**/*"):
                if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    try:
                        blacklist.add(compute_file_sha256(f))
                    except Exception:
                        pass
    print(f"Loaded {len(blacklist)} unique holdout SHA256 hashes into blacklist.")
    return blacklist


def fetch_json(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def fetch_all_met_candidates():
    query_list = [
        "carpet", "rug", "kilim", "prayer rug", "ushak", "oushak", "ladik", "hereke",
        "bergama", "ghiordes", "gordes", "holbein", "lotto", "flatweave", "sumak",
        "soumak", "shirvan", "kazak", "karabagh", "daghestan", "khorasan", "tabriz",
        "kashan", "isfahan", "herat", "tapestry", "weaving"
    ]

    all_oids = set()
    print("Querying Met Museum Open Access API across carpet/rug queries...")
    for q in query_list:
        url = f"https://collectionapi.metmuseum.org/public/collection/v1/search?hasImages=true&isPublicDomain=true&q={urllib.parse.quote(q)}"
        data = fetch_json(url)
        if data:
            oids = data.get("objectIDs") or []
            for oid in oids:
                all_oids.add(oid)

    print(f"Total distinct candidate Met objectIDs discovered: {len(all_oids)}")
    return sorted(list(all_oids))


def get_met_object_detail(oid: int):
    url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}"
    data = fetch_json(url)
    if not data or not data.get("isPublicDomain"):
        return None

    img_url = data.get("primaryImage")
    if not img_url or not img_url.startswith("http"):
        return None

    title = (data.get("title") or "").lower()
    obj_name = (data.get("objectName") or "").lower()
    medium = (data.get("medium") or "").lower()
    dept = (data.get("department") or "").lower()
    classification = (data.get("classification") or "").lower()

    combined = f"{title} {obj_name} {medium} {dept} {classification}"

    # Exclude non-textiles
    exclude_terms = ["folio", "manuscript", "paper", "stonepaste", "ceramic", "bowl", "coin", "sword", "armor", "painting on canvas", "oil on canvas", "drawing", "print", "photograph", "tile", "pottery", "glass", "sculpture", "statue", "furniture"]
    if any(ex in combined for ex in exclude_terms):
        return None

    # Must match textile / carpet / weaving
    include_terms = ["carpet", "rug", "kilim", "textile", "tapestry", "weaving", "wool", "silk", "pile", "knot", "velvet", "embroidery", "cushion", "hanging", "panel", "cover", "mat", "runner", "flatweave"]
    if not any(inc in combined for inc in include_terms):
        return None

    return {
        "institution": "Metropolitan Museum of Art",
        "institution_code": "MET",
        "object_id": str(oid),
        "accession_number": data.get("accessionNumber") or str(oid),
        "title": data.get("title") or f"Met Object {oid}",
        "culture": data.get("culture") or data.get("period") or "Islamic / Near Eastern / European",
        "period": data.get("period") or data.get("objectDate") or "",
        "object_date": data.get("objectDate") or "",
        "image_url": img_url,
        "source_url": data.get("objectURL") or f"https://www.metmuseum.org/art/collection/search/{oid}",
        "license": "CC0 1.0 Universal (Public Domain)",
        "rights_statement": "Public Domain / CC0 Open Access",
    }


def download_and_validate(candidate: dict, holdout_blacklist: set):
    img_url = candidate["image_url"]
    try:
        req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) < 10000:
                return None, "file_too_small"

            sha256 = compute_sha256(data)
            if sha256 in holdout_blacklist:
                return None, "holdout_collision"

            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return None, "decode_error"

            h, w = img.shape[:2]
            if min(h, w) < 640:
                return None, "short_edge_too_small"

            candidate["width"] = int(w)
            candidate["height"] = int(h)
            candidate["sha256"] = sha256
            candidate["image_bytes"] = data
            return candidate, "success"
    except Exception as e:
        return None, f"download_error: {e}"


def main():
    print("=" * 80)
    print("MET CORPUS AUGMENTATION & LICENSE SEGREGATION (Y6.5)")
    print("=" * 80)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    holdout_blacklist = load_holdout_blacklist()

    # Step 1: Load existing corpus metadata & fix license strings
    existing_entries = []
    seen_corpus_hashes = set()
    existing_met_count = 0

    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("institution") == "Victoria and Albert Museum":
                        item["license"] = "V&A Open Access (CC BY-NC-SA / Non-Commercial & Educational)"
                        item["rights_statement"] = "V&A Open Access / Review Needed for Commercial Training"
                    elif item.get("institution") == "Metropolitan Museum of Art":
                        item["license"] = "CC0 1.0 Universal (Public Domain)"
                        item["rights_statement"] = "Public Domain / CC0 Open Access"
                        existing_met_count += 1

                    existing_entries.append(item)
                    seen_corpus_hashes.add(item["sha256"])

    print(f"Existing corpus records loaded: {len(existing_entries)} (Met count: {existing_met_count})")

    needed_met = max(0, TARGET_MET_TOTAL - existing_met_count)
    print(f"Target total Met images: {TARGET_MET_TOTAL} (Need to fetch: {needed_met})")

    new_saved_entries = []
    rejection_stats = {
        "holdout_collision": 0,
        "short_edge_too_small": 0,
        "duplicate_in_corpus": 0,
        "download_error": 0,
        "file_too_small": 0,
        "decode_error": 0,
    }

    if needed_met > 0:
        met_oids = fetch_all_met_candidates()
        print(f"Fetching details for {len(met_oids)} Met objects in parallel...")
        met_candidates = []
        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = {executor.submit(get_met_object_detail, oid): oid for oid in met_oids}
            for fut in as_completed(futures):
                res = fut.result()
                if res:
                    met_candidates.append(res)

        print(f"Discovered {len(met_candidates)} verified Met textile/carpet candidates.")

        current_idx = len(existing_entries)
        print(f"Downloading new Met images (Target: {needed_met} new images)...")

        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(download_and_validate, c, holdout_blacklist) for c in met_candidates]
            for fut in as_completed(futures):
                cand, reason = fut.result()
                if cand is None:
                    if "download_error" in reason:
                        rejection_stats["download_error"] += 1
                    elif reason in rejection_stats:
                        rejection_stats[reason] += 1
                    continue

                sha = cand["sha256"]
                if sha in seen_corpus_hashes:
                    rejection_stats["duplicate_in_corpus"] += 1
                    continue
                seen_corpus_hashes.add(sha)

                current_idx += 1
                filename = f"real_carpet_corpus_{current_idx:04d}.jpg"
                img_path = IMAGES_DIR / filename

                with open(img_path, "wb") as f:
                    f.write(cand["image_bytes"])

                meta_record = {
                    "corpus_id": f"real_corpus_{current_idx:04d}",
                    "filename": filename,
                    "institution": cand["institution"],
                    "institution_code": cand["institution_code"],
                    "object_id": cand["object_id"],
                    "accession_number": cand["accession_number"],
                    "title": cand["title"],
                    "culture_period": cand["culture"],
                    "period": cand["period"],
                    "object_date": cand["object_date"],
                    "width": cand["width"],
                    "height": cand["height"],
                    "sha256": sha,
                    "source_url": cand["source_url"],
                    "image_url": cand["image_url"],
                    "license": "CC0 1.0 Universal (Public Domain)",
                    "rights_statement": "Public Domain / CC0 Open Access",
                }
                new_saved_entries.append(meta_record)

                if len(new_saved_entries) % 5 == 0:
                    print(f"  [Progress] Acquired {len(new_saved_entries)}/{needed_met} new Met images...")

                if len(new_saved_entries) >= needed_met:
                    print(f"Reached target of {needed_met} new Met images. Stopping collection.")
                    break

    all_entries = existing_entries + new_saved_entries

    # Save updated metadata.jsonl
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Segregate Licenses
    training_safe_list = []
    review_needed_list = []

    for e in all_entries:
        lic = (e.get("license") or "").lower()
        if "cc0" in lic or ("public domain" in lic and "v&a" not in lic and "nc" not in lic):
            training_safe_list.append(e)
        else:
            review_needed_list.append(e)

    institution_counts = {}
    license_counts = {}
    for e in all_entries:
        inst = e["institution"]
        institution_counts[inst] = institution_counts.get(inst, 0) + 1
        lic = e["license"]
        license_counts[lic] = license_counts.get(lic, 0) + 1

    met_count = institution_counts.get("Metropolitan Museum of Art", 0)
    va_count = institution_counts.get("Victoria and Albert Museum", 0)
    total_count = len(all_entries)
    met_ratio = (met_count / total_count) if total_count > 0 else 0.0

    manifest_data = {
        "dataset_name": "real_corpus_v1",
        "dataset_version": "v1.1.0-balanced",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_images": total_count,
        "met_image_count": met_count,
        "va_image_count": va_count,
        "met_share_ratio": round(met_ratio, 4),
        "met_share_percentage": f"{met_ratio * 100:.2f}%",
        "institution_breakdown": institution_counts,
        "license_breakdown": license_counts,
        "holdout_collision_count": rejection_stats["holdout_collision"],
        "holdout_leakage_prohibition_verified": rejection_stats["holdout_collision"] == 0,
        "license_segregation": {
            "policy_rule": "review_needed kovası ticari model eğitiminde kullanılmaz; Y7 yalnızca training_safe kovasını tüketir.",
            "training_safe_count": len(training_safe_list),
            "review_needed_count": len(review_needed_list),
            "training_safe_filenames": [e["filename"] for e in training_safe_list],
            "review_needed_filenames": [e["filename"] for e in review_needed_list],
        },
        "rejection_statistics": rejection_stats,
        "metadata_file": str(METADATA_FILE.relative_to(ROOT_DIR)).replace("\\", "/"),
        "images_directory": str(IMAGES_DIR.relative_to(ROOT_DIR)).replace("\\", "/"),
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("MET AUGMENTATION & LICENSE SEGREGATION SUMMARY")
    print(f"Total Images in Corpus:        {total_count}")
    print(f"Met Museum Image Count:        {met_count} ({met_ratio * 100:.2f}%) [Target >= 25%]")
    print(f"V&A Museum Image Count:        {va_count}")
    print(f"Training Safe Bucket (CC0):    {len(training_safe_list)}")
    print(f"Review Needed Bucket (NC):     {len(review_needed_list)}")
    print(f"Holdout Collision Count:       {rejection_stats['holdout_collision']} (MUST BE 0)")
    print(f"Updated Manifest:              {MANIFEST_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
