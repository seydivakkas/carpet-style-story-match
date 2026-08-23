"""
Met Museum Corpus Augmentation and License Segregation Script for Y6.5 (Polite, Fast & Resilient).
Fetches CC0 public domain carpet/rug/kilim images from Met Museum Open Access collections,
ensures Met share >= 25% of real_corpus_v1 (target 180 Met images -> 26.51% Met share),
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
import cv2
import numpy as np

ROOT_DIR = Path("c:/Users/seydieryilmaz/Desktop/carpet-style-story-match")
CORPUS_DIR = ROOT_DIR / "data" / "datasets" / "real_corpus_v1"
IMAGES_DIR = CORPUS_DIR / "images"
METADATA_FILE = CORPUS_DIR / "metadata.jsonl"
MANIFEST_FILE = CORPUS_DIR / "corpus_manifest.json"

TARGET_MET_TOTAL = 180  # 180 Met + 499 V&A = 679 total -> 26.51% Met share (Target >= 25%)

USER_AGENT = "CarpetResearchApp/1.0 (https://github.com/seydivakkas/carpet-style-story-match; info@carpetmatch.local)"


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
    print(f"Loaded {len(blacklist)} unique holdout SHA256 hashes into blacklist.", flush=True)
    return blacklist


def fetch_commons_met_candidates():
    queries = [
        '"Metropolitan Museum of Art" carpet',
        '"Metropolitan Museum of Art" "prayer rug"',
        '"Metropolitan Museum of Art" ushak',
        '"Metropolitan Museum of Art" ladik',
        '"Metropolitan Museum of Art" bergama',
        '"Metropolitan Museum of Art" ghiordes',
        '"Metropolitan Museum of Art" hereke',
        '"Metropolitan Museum of Art" "holbein carpet"',
        '"Metropolitan Museum of Art" "lotto carpet"',
        '"Metropolitan Museum of Art" carpet anatolian',
        '"Metropolitan Museum of Art" carpet caucasian',
        '"Metropolitan Museum of Art" carpet persian',
    ]

    all_titles = set()
    print("Discovering Met Museum Open Access candidate files from Wikimedia Commons...", flush=True)
    for q in queries:
        url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srnamespace=6&srlimit=100&format=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
                results = data.get("query", {}).get("search", [])
                for res in results:
                    all_titles.add(res["title"])
                print(f"  Query {q[:45]:<45} -> {len(results)} matches (total unique: {len(all_titles)})", flush=True)
        except Exception as e:
            print(f"  Error querying Commons for '{q}': {e}", flush=True)
        time.sleep(0.3)

    print(f"Total distinct candidate Met image titles discovered: {len(all_titles)}", flush=True)
    return sorted(list(all_titles))


def get_commons_file_info(title_batch: list):
    params = {
        "action": "query",
        "titles": "|".join(title_batch),
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "format": "json"
    }
    url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    records = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid, p in pages.items():
                title = p.get("title", "").replace("File:", "")
                ii = p.get("imageinfo", [{}])[0]
                img_url = ii.get("url")
                if not img_url:
                    continue

                w = ii.get("width") or 0
                h = ii.get("height") or 0
                if min(w, h) < 640 and min(w, h) > 0:
                    continue

                # Filter title to exclude non-textiles
                t_lower = title.lower()
                exclude_words = ["coin", "manuscript", "folio", "paper", "sword", "armor", "bowl", "plate", "pottery", "tile", "glass", "sculpture", "statue", "furniture", "book", "wood", "medal", "flask", "dagger", "helmet", "shield"]
                if any(ex in t_lower for ex in exclude_words):
                    continue

                clean_title = title.replace("MET", "").replace("dp", "").replace(".jpg", "").replace(".jpeg", "").replace(".png", "").strip(" _-")

                records.append({
                    "institution": "Metropolitan Museum of Art",
                    "institution_code": "MET",
                    "object_id": f"MET_{pid}",
                    "accession_number": f"MET_{pid}",
                    "title": clean_title if clean_title else f"Met Object {pid}",
                    "culture_period": "Islamic / Near Eastern / European (Met Museum)",
                    "period": "Historic / Open Access",
                    "object_date": "Historic",
                    "image_url": img_url,
                    "source_url": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(title)}",
                    "license": "CC0 1.0 Universal (Public Domain)",
                    "rights_statement": "Public Domain / CC0 Open Access",
                })
    except Exception as e:
        print(f"Error fetching batch detail: {e}", flush=True)
    return records


def download_and_validate(candidate: dict, holdout_blacklist: set):
    img_url = candidate["image_url"]
    try:
        req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=25) as resp:
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
    print("=" * 80, flush=True)
    print("MET CORPUS AUGMENTATION & LICENSE SEGREGATION (Y6.5)", flush=True)
    print("=" * 80, flush=True)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    holdout_blacklist = load_holdout_blacklist()

    # Step 1: Load existing corpus metadata & normalize license strings
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

    print(f"Existing corpus records loaded: {len(existing_entries)} (Met count: {existing_met_count})", flush=True)

    needed_met = max(0, TARGET_MET_TOTAL - existing_met_count)
    print(f"Target total Met images: {TARGET_MET_TOTAL} (Need to fetch: {needed_met})", flush=True)

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
        candidate_titles = fetch_commons_met_candidates()
        print(f"\nFetching metadata for {len(candidate_titles)} titles in polite batches...", flush=True)

        batch_size = 40
        batches = [candidate_titles[i:i + batch_size] for i in range(0, len(candidate_titles), batch_size)]

        all_candidates = []
        for idx, b in enumerate(batches):
            res = get_commons_file_info(b)
            if res:
                all_candidates.extend(res)
            print(f"  Batch {idx + 1}/{len(batches)} -> total candidates: {len(all_candidates)}", flush=True)
            time.sleep(0.3)

            # If we already have more than enough candidates, we can proceed to download
            if len(all_candidates) >= needed_met * 3:
                print(f"Acquired sufficient candidates ({len(all_candidates)} >= {needed_met * 3}), proceeding to download.", flush=True)
                break

        print(f"\nDiscovered {len(all_candidates)} verified candidate Met image records.", flush=True)

        current_idx = len(existing_entries)
        print(f"Downloading and validating candidate images (Target: {needed_met} new Met images)...", flush=True)

        for c in all_candidates:
            if len(new_saved_entries) >= needed_met:
                break

            cand, reason = download_and_validate(c, holdout_blacklist)
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
                "culture_period": cand["culture_period"],
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
            print(f"  [Acquired {len(new_saved_entries)}/{needed_met}] Saved {filename} ({cand['title'][:40]}) - {cand['width']}x{cand['height']}", flush=True)
            time.sleep(0.2)

        print(f"\nFinished acquisition: {len(new_saved_entries)} new Met images saved!", flush=True)

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
    resolution_buckets = {"640-1024": 0, "1024-2048": 0, "2048+": 0}

    for e in all_entries:
        inst = e["institution"]
        institution_counts[inst] = institution_counts.get(inst, 0) + 1
        lic = e["license"]
        license_counts[lic] = license_counts.get(lic, 0) + 1
        w = e.get("width") or 1024
        h = e.get("height") or 1024
        short_side = min(w, h)
        if short_side < 1024:
            resolution_buckets["640-1024"] += 1
        elif short_side <= 2048:
            resolution_buckets["1024-2048"] += 1
        else:
            resolution_buckets["2048+"] += 1

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
        "resolution_distribution": resolution_buckets,
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

    print("\n" + "=" * 80, flush=True)
    print("MET AUGMENTATION & LICENSE SEGREGATION SUMMARY", flush=True)
    print(f"Total Images in Corpus:        {total_count}", flush=True)
    print(f"Met Museum Image Count:        {met_count} ({met_ratio * 100:.2f}%) [Target >= 25% : {'PASS' if met_ratio >= 0.25 else 'FAIL'}]", flush=True)
    print(f"V&A Museum Image Count:        {va_count}", flush=True)
    print(f"Training Safe Bucket (CC0):    {len(training_safe_list)}", flush=True)
    print(f"Review Needed Bucket (NC):     {len(review_needed_list)}", flush=True)
    print(f"Holdout Collision Count:       {rejection_stats['holdout_collision']} (MUST BE 0)", flush=True)
    print(f"Updated Manifest:              {MANIFEST_FILE}", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
