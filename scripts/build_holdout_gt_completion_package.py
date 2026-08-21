"""
Packages Holdout Dataset for CVAT/Roboflow GT completion and sets up real corpus annotations skeleton.
Author: Seydi Eryilmaz (@seydivakkas)
Copyright (c) 2026 Seydi Eryilmaz - All Rights Reserved
"""

import os
import json
import shutil
from pathlib import Path

ROOT_DIR = Path("c:/Users/seydieryilmaz/Desktop/carpet-style-story-match")
REAL_CORPUS_DIR = ROOT_DIR / "data" / "datasets" / "real_corpus_v1"
HOLDOUT_SRC_DIR = ROOT_DIR / "data" / "datasets" / "real-motif-benchmark-v1"
COMPLETION_DIR = ROOT_DIR / "data" / "datasets" / "holdout_gt_completion"

CLASSES = [
    "cloud_band_like",
    "comb_like",
    "hook_like",
    "horn_like",
    "human_figure_like_geometric",
    "lattice_like",
    "lotus_like",
    "lozenge_like",
    "medallion_like",
    "niche_like",
    "octagonal_form",
    "palmette_like",
    "rosette_like",
    "star_like",
    "tree_like",
    "unmapped_visual_motif",
    "vine_scroll_like",
]

SYNONYM_MAP = {
    "ram_horn_like": "horn_like",
    "tree_of_life_like": "tree_like",
    "medallion": "medallion_like",
    "mihrab_like": "niche_like",
    "niche": "niche_like",
    "star": "star_like",
    "hand_like": "human_figure_like_geometric",
    "hair_clip_like": "unmapped_visual_motif",
    "running_water_like": "vine_scroll_like",
    "scorpion_like": "unmapped_visual_motif",
    "cross_like": "unmapped_visual_motif",
    "eye_like": "unmapped_visual_motif",
    "dragon_like": "unmapped_visual_motif",
    "phoenix_like": "unmapped_visual_motif",
}


def main():
    print("=" * 80)
    print("SETTING UP ANNOTATION SKELETON & HOLDOUT GT COMPLETION PACKAGE")
    print("=" * 80)

    # 1. Real Corpus annotations directory & classes.txt
    corpus_annotations_dir = REAL_CORPUS_DIR / "annotations"
    corpus_annotations_dir.mkdir(parents=True, exist_ok=True)
    corpus_classes_file = REAL_CORPUS_DIR / "classes.txt"

    with open(corpus_classes_file, "w", encoding="utf-8") as f:
        for c in CLASSES:
            f.write(c + "\n")
    print(f"Created real corpus classes.txt at: {corpus_classes_file}")
    print(f"Created empty annotations directory at: {corpus_annotations_dir}")

    # 2. Holdout Completion Package
    comp_images_dir = COMPLETION_DIR / "images"
    comp_labels_dir = COMPLETION_DIR / "labels"
    comp_images_dir.mkdir(parents=True, exist_ok=True)
    comp_labels_dir.mkdir(parents=True, exist_ok=True)

    # Copy classes.txt
    with open(COMPLETION_DIR / "classes.txt", "w", encoding="utf-8") as f:
        for c in CLASSES:
            f.write(c + "\n")

    # Create data.yaml
    data_yaml_content = f"""path: {COMPLETION_DIR.as_posix()}
train: images
val: images
test: images
nc: {len(CLASSES)}
names: {CLASSES}
"""
    with open(COMPLETION_DIR / "data.yaml", "w", encoding="utf-8") as f:
        f.write(data_yaml_content)

    # Load existing 35 holdout annotations
    with open(HOLDOUT_SRC_DIR / "annotations.json", "r", encoding="utf-8") as f:
        holdout_data = json.load(f)["data"]

    class_to_id = {c: i for i, c in enumerate(CLASSES)}
    total_exported_boxes = 0

    for item in holdout_data:
        fname = item["filename"]
        src_img = HOLDOUT_SRC_DIR / "images" / fname
        dst_img = comp_images_dir / fname

        if src_img.exists():
            shutil.copy2(src_img, dst_img)

        w = float(item["width"])
        h = float(item["height"])

        txt_lines = []
        for inst in item["instances"]:
            raw_k = inst.get("visual_candidate_key") or "unmapped_visual_motif"
            norm_k = SYNONYM_MAP.get(raw_k, raw_k)
            if norm_k not in class_to_id:
                norm_k = "unmapped_visual_motif"
            cid = class_to_id[norm_k]

            # BBox format
            bbox = inst["bbox_xyxy"]
            x1, y1, x2, y2 = bbox
            xc = ((x1 + x2) / 2.0) / w
            yc = ((y1 + y2) / 2.0) / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h

            # Clamp coordinates to [0, 1]
            xc = min(1.0, max(0.0, xc))
            yc = min(1.0, max(0.0, yc))
            bw = min(1.0, max(0.0, bw))
            bh = min(1.0, max(0.0, bh))

            txt_lines.append(f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
            total_exported_boxes += 1

        label_name = Path(fname).stem + ".txt"
        with open(comp_labels_dir / label_name, "w", encoding="utf-8") as lf:
            lf.write("\n".join(txt_lines) + ("\n" if txt_lines else ""))

    # Copy annotations.json to completion directory
    shutil.copy2(HOLDOUT_SRC_DIR / "annotations.json", COMPLETION_DIR / "annotations.json")

    # Write README.md for human annotator
    readme_content = f"""# Holdout Ground Truth (GT) Tamamlama Paketi

Bu paket, **`real-motif-benchmark-v1`** holdout test kümesindeki **35 gerçek halı görselini** ve mevcut **92 adet doğrulanmış GT kutusunu** Roboflow / CVAT araçlarına doğrudan aktarılabilir formatta içerir.

## Amacı
Mevcut holdout test setinde 17 sınıfın 5 tanesinin (`cloud_band_like`, `lotus_like`, `medallion_like`, `octagonal_form`, `palmette_like`) GT desteği 0'dır. Bu durum, model kapı kontrolünde bu sınıfların gerçek dünya başarısının ölçülmesini engellemektedir (örneğin Uşak madalyonlu halılardaki belirgin merkezi madalyon kutusu eksiktir).

## İçerik
- `images/`: 35 adet holdout halı görseli (`real_carpet_001.jpg` - `real_carpet_035.jpg`)
- `labels/`: Her görsel için mevcut 92 GT kutusunu içeren YOLO formatlı `.txt` dosyaları
- `classes.txt`: 17 motif sınıfı (YOLO index sırasıyla)
- `data.yaml`: YOLOv11 uyumlu veri seti manifestosu
- `annotations.json`: Detaylı JSON formatlı anotasyonlar

## Nasıl Yüklenir (Roboflow / CVAT)
1. **Roboflow**: "Upload Data" -> `images/` ve `labels/` klasörlerini birlikte sürükleyip bırakın (Format: YOLOv11 / YOLOv8 Annotation).
2. **CVAT**: Yeni görev oluşturun, görselleri yükleyin ve "Upload Annotations -> YOLO 1.1" seçeneğiyle `labels/` klasörünü yükleyin.
3. Kılavuzdaki kurallara göre (`docs/labeling-guide-v1.md`) eksik madalyon, palmet, nilüfer ve sekizgen kutularını ekleyin.

Toplam Görsel: 35
Mevcut GT Kutusu: {total_exported_boxes}
Sınıf Sayısı: {len(CLASSES)}
"""
    with open(COMPLETION_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\nHoldout GT completion package created at: {COMPLETION_DIR}")
    print(f"Exported {len(holdout_data)} images and {total_exported_boxes} GT boxes.")
    print("=" * 80)


if __name__ == "__main__":
    main()
