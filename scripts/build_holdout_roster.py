import json
import hashlib
import time
from pathlib import Path

BENCHMARK_DIR = Path("data/datasets/real-motif-benchmark-v1")
IMAGES_DIR = BENCHMARK_DIR / "images"
ANNOTATIONS_FILE = BENCHMARK_DIR / "annotations.json"
ROSTER_FILE = BENCHMARK_DIR / "holdout_roster.json"

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

with open(ANNOTATIONS_FILE, "r", encoding="utf-8") as f:
    ann_data = json.load(f)

ann_records = {item["filename"]: item for item in ann_data.get("data", [])}

images = sorted(list(IMAGES_DIR.glob("*.jpg")))
print(f"Total image files in benchmark directory: {len(images)}")

roster_items = []
total_gt_boxes = 0
gate_members_count = 0
holdout_unannotated_count = 0

for img in images:
    fname = img.name
    sha256 = compute_sha256(img)
    
    if fname in ann_records:
        ann = ann_records[fname]
        instances = ann.get("instances", [])
        box_count = len(instances)
        is_gate_member = True
        gate_members_count += 1
        total_gt_boxes += box_count
        role = "gate_evaluation"
    else:
        box_count = 0
        is_gate_member = False
        holdout_unannotated_count += 1
        role = "holdout_unannotated"
        
    roster_items.append({
        "filename": fname,
        "sha256": sha256,
        "gt_box_count": box_count,
        "gate_member": is_gate_member,
        "role": role,
    })

roster_data = {
    "benchmark_name": "real-motif-benchmark-v1",
    "roster_version": "v1.0.0",
    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "total_images_in_pool": len(images),
    "gate_member_count": gate_members_count,
    "holdout_unannotated_count": holdout_unannotated_count,
    "total_gt_boxes": total_gt_boxes,
    "gate_measurement_policy": "Kapı ölçümleri (gate measurements) yalnızca gate_member=true olan 35 GT'li görsel üzerinde icra edilir.",
    "images": roster_items,
}

with open(ROSTER_FILE, "w", encoding="utf-8") as f:
    json.dump(roster_data, f, indent=2, ensure_ascii=False)

print(f"Holdout roster successfully generated: {ROSTER_FILE}")
print(f"  Total pool: {len(images)} images")
print(f"  Gate members (GT > 0): {gate_members_count}")
print(f"  Holdout unannotated (GT = 0): {holdout_unannotated_count}")
print(f"  Total GT bounding boxes: {total_gt_boxes}")
