"""
Real Carpet Corpus Builder for V2-10 / Y6 Campaign.
Fetches public-domain real carpet imagery from Met Museum and V&A APIs.
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

TARGET_MIN_IMAGES = 300
TARGET_MAX_IMAGES = 500

USER_AGENT = "CarpetResearchBot/1.0 (contact: info@carpet-match.local; research evaluation)"


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


def fetch_met_objects():
    queries = [
        "carpet", "rug", "kilim", "prayer rug", "oriental carpet", "turkish carpet",
        "anatolian carpet", "persian carpet", "caucasian carpet", "ushak", "bergama",
        "hereke", "gordes", "ladik", "kula", "milas"
    ]
    object_ids = set()
    print("Searching Met Museum Open Access API...")
    for q in queries:
        url = f"https://collectionapi.metmuseum.org/public/collection/v1/search?q={urllib.parse.quote(q)}&isPublicDomain=true"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                oids = data.get("objectIDs") or []
                for oid in oids:
                    object_ids.add(oid)
            time.sleep(0.1)
        except Exception as e:
            print(f"Error querying Met for '{q}': {e}")

    print(f"Total candidate Met Museum objectIDs found: {len(object_ids)}")
    return sorted(list(object_ids))


def get_met_object_detail(oid: int):
    url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data.get("isPublicDomain"):
                return None
            img_url = data.get("primaryImage")
            if not img_url or not img_url.startswith("http"):
                return None
            # Filter title / classification / medium to be carpet/textile relevant
            title = (data.get("title") or "").lower()
            obj_name = (data.get("objectName") or "").lower()
            medium = (data.get("medium") or "").lower()
            dept = (data.get("department") or "").lower()
            text_combo = f"{title} {obj_name} {medium} {dept}"

            # Ensure textile/carpet relevance or exclusion of pure paintings/prints
            keywords = ["carpet", "rug", "kilim", "textile", "weaving", "tapestry", "wool", "silk", "pile", "knot", "islamic"]
            if not any(k in text_combo for k in keywords):
                return None

            return {
                "institution": "Metropolitan Museum of Art",
                "institution_code": "MET",
                "object_id": str(oid),
                "accession_number": data.get("accessionNumber") or str(oid),
                "title": data.get("title") or f"Met Object {oid}",
                "culture": data.get("culture") or data.get("period") or "Islamic / Near Eastern",
                "period": data.get("period") or data.get("objectDate") or "",
                "object_date": data.get("objectDate") or "",
                "image_url": img_url,
                "source_url": data.get("objectURL") or f"https://www.metmuseum.org/art/collection/search/{oid}",
                "license": "CC0 1.0 Universal (Public Domain)",
                "rights_statement": "Public Domain / CC0 Open Access",
            }
    except Exception:
        return None


def fetch_va_objects():
    queries = ["carpet", "rug", "kilim", "prayer rug", "anatolian carpet", "turkish carpet", "persian carpet"]
    records = []
    seen_sys = set()
    print("Searching Victoria and Albert Museum (V&A) API...")
    for q in queries:
        page = 1
        max_pages = 4  # 100 per page = up to 400 per query
        while page <= max_pages:
            url = f"https://api.vam.ac.uk/v2/objects/search?q={urllib.parse.quote(q)}&images_exist=1&page_size=100&page={page}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    recs = data.get("records") or []
                    if not recs:
                        break
                    for r in recs:
                        sys_num = r.get("systemNumber")
                        img_id = r.get("_primaryImageId")
                        if not sys_num or not img_id or sys_num in seen_sys:
                            continue
                        seen_sys.add(sys_num)

                        title = r.get("_primaryTitle") or r.get("objectType") or "Carpet / Rug"
                        place = r.get("_primaryPlace") or "Near East / Europe"
                        maker_info = r.get("_primaryMaker") or {}
                        maker = maker_info.get("name") if isinstance(maker_info, dict) else str(maker_info)
                        date_str = r.get("_primaryDate") or ""

                        # IIIF URL for high quality 1024x1024 or full image
                        img_url = f"https://framemark.vam.ac.uk/collections/{img_id}/full/!1024,1024/0/default.jpg"

                        records.append({
                            "institution": "Victoria and Albert Museum",
                            "institution_code": "V&A",
                            "object_id": sys_num,
                            "accession_number": r.get("accessionNumber") or sys_num,
                            "title": title,
                            "culture": place,
                            "period": date_str,
                            "object_date": date_str,
                            "image_url": img_url,
                            "source_url": f"https://collections.vam.ac.uk/item/{sys_num}/",
                            "license": "Public Domain / V&A Open Access (Educational/Non-Commercial & CC BY-NC-SA / Open Content)",
                            "rights_statement": "Open Access / Public Collection Reference",
                        })
                    if len(recs) < 100:
                        break
                    page += 1
                time.sleep(0.1)
            except Exception as e:
                print(f"Error querying V&A for '{q}' page {page}: {e}")
                break

    print(f"Total candidate V&A records found: {len(records)}")
    return records


def download_and_validate_image(candidate: dict, holdout_blacklist: set):
    """
    Downloads image, checks dimensions (short edge >= 640px), computes sha256,
    verifies no holdout collision.
    """
    img_url = candidate["image_url"]
    try:
        req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            if len(data) < 10000:  # < 10KB is likely placeholder or error
                return None, "file_too_small"

            sha256 = compute_sha256(data)
            if sha256 in holdout_blacklist:
                return None, "holdout_collision"

            # Decode image
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return None, "decode_error"

            h, w = img.shape[:2]
            short_edge = min(h, w)
            if short_edge < 640:
                # If slightly below (e.g. 500-639) from IIIF, try downloading full res if V&A or check if acceptable
                if "framemark.vam.ac.uk" in img_url and short_edge >= 480:
                    # Retry with full resolution
                    full_url = img_url.replace("!1024,1024", "full")
                    try:
                        req_full = urllib.request.Request(full_url, headers={"User-Agent": USER_AGENT})
                        with urllib.request.urlopen(req_full, timeout=25) as f_resp:
                            f_data = f_resp.read()
                            f_arr = np.frombuffer(f_data, np.uint8)
                            f_img = cv2.imdecode(f_arr, cv2.IMREAD_COLOR)
                            if f_img is not None and min(f_img.shape[:2]) >= 640:
                                img = f_img
                                data = f_data
                                h, w = img.shape[:2]
                                sha256 = compute_sha256(data)
                                if sha256 in holdout_blacklist:
                                    return None, "holdout_collision"
                            else:
                                return None, "short_edge_too_small"
                    except Exception:
                        return None, "short_edge_too_small"
                else:
                    return None, "short_edge_too_small"

            candidate["width"] = int(w)
            candidate["height"] = int(h)
            candidate["sha256"] = sha256
            candidate["image_bytes"] = data
            return candidate, "success"
    except Exception as e:
        return None, f"download_failed: {e}"


def main():
    print("=" * 80)
    print("STARTING REAL CARPET CORPUS BUILDER (V2-10 / Y6)")
    print("=" * 80)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    holdout_blacklist = load_holdout_blacklist()

    # Step 1: Query Met Museum & V&A APIs
    met_oids = fetch_met_objects()
    va_candidates = fetch_va_objects()

    # Fetch Met object details in parallel
    print(f"\nFetching Met Museum object metadata for {len(met_oids)} IDs...")
    met_candidates = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_met_object_detail, oid): oid for oid in met_oids}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                met_candidates.append(res)

    print(f"Retained {len(met_candidates)} public-domain textile/carpet Met candidates with primary images.")

    # Combine candidates
    all_candidates = met_candidates + va_candidates
    print(f"Total pool size before download & dimension verification: {len(all_candidates)}")

    # Step 2: Download & Filter
    saved_entries = []
    seen_corpus_hashes = set()
    rejection_stats = {
        "holdout_collision": 0,
        "short_edge_too_small": 0,
        "duplicate_in_corpus": 0,
        "download_failed": 0,
        "file_too_small": 0,
        "decode_error": 0,
    }

    print(f"\nDownloading and filtering candidates (Target: {TARGET_MIN_IMAGES}-{TARGET_MAX_IMAGES} images)...")
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(download_and_validate_image, c, holdout_blacklist) for c in all_candidates]
        for fut in as_completed(futures):
            cand, reason = fut.result()
            if cand is None:
                if "download_failed" in reason:
                    rejection_stats["download_failed"] += 1
                elif reason in rejection_stats:
                    rejection_stats[reason] += 1
                continue

            sha = cand["sha256"]
            if sha in seen_corpus_hashes:
                rejection_stats["duplicate_in_corpus"] += 1
                continue
            seen_corpus_hashes.add(sha)

            idx = len(saved_entries) + 1
            filename = f"real_carpet_corpus_{idx:04d}.jpg"
            img_path = IMAGES_DIR / filename

            with open(img_path, "wb") as f:
                f.write(cand["image_bytes"])

            meta_record = {
                "corpus_id": f"real_corpus_{idx:04d}",
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
                "license": cand["license"],
                "rights_statement": cand["rights_statement"],
            }
            saved_entries.append(meta_record)

            if len(saved_entries) % 25 == 0 or len(saved_entries) == TARGET_MAX_IMAGES:
                print(f"  [Progress] Successfully acquired {len(saved_entries)} corpus images...")

            if len(saved_entries) >= TARGET_MAX_IMAGES:
                print(f"Reached upper target of {TARGET_MAX_IMAGES} images. Stopping collection.")
                break

    print(f"\nCorpus collection finished: {len(saved_entries)} valid images saved!")

    # Step 3: Write metadata.jsonl
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        for entry in saved_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Step 4: Write corpus_manifest.json
    institution_counts = {}
    license_counts = {}
    resolution_buckets = {"640-1024": 0, "1024-2048": 0, "2048+": 0}

    for e in saved_entries:
        inst = e["institution"]
        institution_counts[inst] = institution_counts.get(inst, 0) + 1
        lic = e["license"]
        license_counts[lic] = license_counts.get(lic, 0) + 1
        short_side = min(e["width"], e["height"])
        if short_side < 1024:
            resolution_buckets["640-1024"] += 1
        elif short_side <= 2048:
            resolution_buckets["1024-2048"] += 1
        else:
            resolution_buckets["2048+"] += 1

    manifest_data = {
        "dataset_name": "real_corpus_v1",
        "dataset_version": "v1.0.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_images": len(saved_entries),
        "target_range": f"{TARGET_MIN_IMAGES}-{TARGET_MAX_IMAGES}",
        "holdout_collision_count": rejection_stats["holdout_collision"],
        "holdout_leakage_prohibition_verified": rejection_stats["holdout_collision"] == 0,
        "institution_breakdown": institution_counts,
        "license_breakdown": license_counts,
        "resolution_distribution": resolution_buckets,
        "rejection_statistics": rejection_stats,
        "metadata_file": str(METADATA_FILE.relative_to(ROOT_DIR)).replace("\\", "/"),
        "images_directory": str(IMAGES_DIR.relative_to(ROOT_DIR)).replace("\\", "/"),
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    print(f"Metadata written to: {METADATA_FILE}")
    print(f"Manifest written to: {MANIFEST_FILE}")
    print(f"Holdout collisions: {rejection_stats['holdout_collision']} (MUST BE 0)")
    print(f"Institution breakdown: {institution_counts}")
    print("=" * 80)


if __name__ == "__main__":
    main()
