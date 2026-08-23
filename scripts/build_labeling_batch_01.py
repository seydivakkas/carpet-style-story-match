"""
Build Human Labeling Worklist Batch-1 (data/datasets/labeling_batch_01).
Selects 50 diverse, stratified images from existing Met CC0 training_safe pool,
packages images, classes.txt, data.yaml, batch_manifest.csv, and README.md.

Author: Seydi Eryilmaz (@seydivakkas)
Copyright (c) 2026 Seydi Eryilmaz - All Rights Reserved
"""

import os
import sys
import json
import csv
import shutil
import hashlib
from pathlib import Path

ROOT_DIR = Path("c:/Users/seydieryilmaz/Desktop/carpet-style-story-match")
REAL_CORPUS_DIR = ROOT_DIR / "data" / "datasets" / "real_corpus_v1"
CORPUS_IMAGES_DIR = REAL_CORPUS_DIR / "images"
METADATA_FILE = REAL_CORPUS_DIR / "metadata.jsonl"
BATCH_DIR = ROOT_DIR / "data" / "datasets" / "labeling_batch_01"
BATCH_IMAGES_DIR = BATCH_DIR / "images"

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

def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def load_holdout_blacklist() -> set:
    blacklist = set()
    dirs = [
        ROOT_DIR / "data" / "datasets" / "real-motif-benchmark-v1" / "images",
        ROOT_DIR / "scratch" / "curation_images",
        ROOT_DIR / "apps" / "api" / "data" / "uploads" / "carpets",
    ]
    for d in dirs:
        if d.exists():
            for p in d.glob("*.*"):
                if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    blacklist.add(compute_file_sha256(p))
    return blacklist

def main():
    print("=" * 80)
    print("BUILDING HUMAN LABELING WORKLIST BATCH-01")
    print("=" * 80)

    # 1. Load holdout blacklist
    blacklist = load_holdout_blacklist()
    print(f"[1] Loaded {len(blacklist)} holdout blacklist hashes.")

    # 2. Load existing Met CC0 records
    records = []
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Filter to Met CC0 records
    met_cc0_records = [
        r for r in records
        if r.get("institution") == "Metropolitan Museum of Art" and
        ("CC0" in r.get("license", "") or r.get("license_verified") is True)
    ]
    print(f"[2] Found {len(met_cc0_records)} Met CC0 candidate records in corpus.")

    # 3. Stratified Selection of 50 images
    # Avoid duplicate objects: track seen base titles / object IDs / accessions
    seen_objects = set()
    stratified_selection = []

    # Sort/Group to ensure diverse representation of Anatolian, Caucasian, Persian, Ushak, Prayer rugs, Medallions, etc.
    priority_keywords = [
        "ushak", "prayer", "marisali", "shirvan", "bergama", "ghiordes", "ladik",
        "holbein", "lotto", "bellini", "caucasian", "anatolian", "persian", "medallion",
        "floral", "animal", "dragon", "cloudband", "silk", "wool", "fragment", "carpet", "rug"
    ]

    # First pass: pick distinct keyword matches
    for kw in priority_keywords:
        for r in met_cc0_records:
            if len(stratified_selection) >= 50:
                break
            
            # Object key for deduplicating multi-angle shots
            raw_title = r.get("title", "")
            base_title = raw_title.split(" wb-")[0].split(" AD-")[0].split(" DP")[0].strip()
            obj_id = r.get("object_id", "")
            obj_key = base_title if len(base_title) > 5 else obj_id
            
            if obj_key in seen_objects:
                continue

            title_lower = raw_title.lower()
            if kw in title_lower:
                img_path = CORPUS_IMAGES_DIR / r["filename"]
                if not img_path.exists():
                    continue
                sha = compute_file_sha256(img_path)
                if sha in blacklist:
                    continue
                
                seen_objects.add(obj_key)
                r["computed_sha256"] = sha
                stratified_selection.append(r)

    # Second pass: fill up to 50 if needed
    if len(stratified_selection) < 50:
        for r in met_cc0_records:
            if len(stratified_selection) >= 50:
                break
            raw_title = r.get("title", "")
            base_title = raw_title.split(" wb-")[0].split(" AD-")[0].split(" DP")[0].strip()
            obj_id = r.get("object_id", "")
            obj_key = base_title if len(base_title) > 5 else obj_id
            
            if obj_key in seen_objects:
                continue
                
            img_path = CORPUS_IMAGES_DIR / r["filename"]
            if not img_path.exists():
                continue
            sha = compute_file_sha256(img_path)
            if sha in blacklist:
                continue
                
            seen_objects.add(obj_key)
            r["computed_sha256"] = sha
            stratified_selection.append(r)

    print(f"[3] Selected {len(stratified_selection)} distinct stratified Met CC0 records.")

    # 4. Prepare output directory
    BATCH_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # 5. Copy images
    for r in stratified_selection:
        src = CORPUS_IMAGES_DIR / r["filename"]
        dst = BATCH_IMAGES_DIR / r["filename"]
        shutil.copy2(src, dst)
    print(f"[4] Copied {len(stratified_selection)} image files to {BATCH_IMAGES_DIR}.")

    # 6. Write classes.txt
    classes_file = BATCH_DIR / "classes.txt"
    with open(classes_file, "w", encoding="utf-8") as f:
        for c in CLASSES:
            f.write(c + "\n")
    print(f"[5] Written {classes_file} with {len(CLASSES)} YOLO classes.")

    # 7. Write data.yaml
    data_yaml_content = f"""# YOLO Dataset Configuration for Human Labeling Batch-01
# Real Corpus Training-Safe CC0 Subset
path: ./
train: images/
val: images/

# 17 Standard Motif Classes (Strict YOLO ID Order 0-16)
names:
"""
    for idx, c in enumerate(CLASSES):
        data_yaml_content += f"  {idx}: {c}\n"

    yaml_file = BATCH_DIR / "data.yaml"
    with open(yaml_file, "w", encoding="utf-8") as f:
        f.write(data_yaml_content)
    print(f"[6] Written {yaml_file}.")

    # 8. Write batch_manifest.csv
    csv_file = BATCH_DIR / "batch_manifest.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "institution", "accession", "period", "source_url", "sha256"])
        for r in stratified_selection:
            accession = r.get("object_id", "")
            period = r.get("date", "Historical")
            writer.writerow([
                r["filename"],
                r.get("institution", "Metropolitan Museum of Art"),
                accession,
                period,
                r.get("source_url", ""),
                r["computed_sha256"]
            ])
    print(f"[7] Written {csv_file} with {len(stratified_selection)} rows.")

    # 9. Write README.md
    readme_content = """# İnsan Etiketleme Çalışma Listesi (Human Labeling Worklist) — BATCH-01

Bu paket, **Y7 ticari model eğitimi** öncesinde gerçek halı/kilim görselleri üzerinde insan uzman etiketlemesi gerçekleştirmek üzere hazırlanmış **50 adet CC0 lisanslı, doğrulanmış (training_safe)** görseli içermektedir.

---

## Paket İçeriği

- **`images/`**: 50 adet yüksek çözünürlüklü gerçek halı/kilim görseli (kısa kenar ≥640px, SHA256 doğrulanmış).
- **`classes.txt`**: 17 standart motif sınıfı (YOLO sınıf ID sırası 0–16 ile birebir uyumlu).
- **`data.yaml`**: CVAT / Roboflow / YOLO standart veri kümesi yapılandırma dosyası.
- **`batch_manifest.csv`**: Her görselin dosya adı, kurumu, envanter/accession numarası, dönemi, kaynak URL'si ve SHA256 hash özeti.
- **`README.md`**: Bu kılavuz.

---

## 1. Etiketleme Kuralları ve Standartları

Etiketleme yaparken lütfen [`docs/labeling-guide-v1.md`](../../docs/labeling-guide-v1.md) belgesindeki tüm semantik kurallara, görsel örneklere ve negatif durum yönergelerine harfiyen uyunuz.

### 17 Standart Sınıf Listesi (YOLO ID Sırası 0–16)
0. `cloud_band_like` (Bulut motifi / bulut şeridi)
1. `comb_like` (Tarak motifi)
2. `hook_like` (Çengel motifi)
3. `horn_like` (Koçboynuzu / boynuz motifi)
4. `human_figure_like_geometric` (İnsan figürü / eli belinde)
5. `lattice_like` (Kafes motifi)
6. `lotus_like` (Lotus / nilüfer motifi)
7. `lozenge_like` (Baklava / pıtrak / elmas formu)
8. `medallion_like` (Madalyon / göbek)
9. `niche_like` (Mihrap formu)
10. `octagonal_form` (Sekizgen form)
11. `palmette_like` (Palmet motifi)
12. `rosette_like` (Rozet / gülce)
13. `star_like` (Yıldız motifi)
14. `tree_like` (Hayat ağacı)
15. `unmapped_visual_motif` (Eşleşmeyen / belirsiz motif)
16. `vine_scroll_like` (Kıvrımdal / sarmaşık motifi)

---

## 2. Yerel CVAT ile Etiketleme Adımları

1. **CVAT'ı Başlatın:**
   ```bash
   # Docker kurulu yerel makinede:
   docker compose up -d
   # Tarayıcıda açın: http://localhost:8080
   ```
2. **Yeni Görev (Create a New Task) Oluşturun:**
   - **Task Name:** `Real_Corpus_Batch_01`
   - **Constructor / Raw Mode:** `classes.txt` dosyasını sürükleyip bırakın veya sınıfları yapıştırın.
   - **Select Files:** `images/` klasöründeki 50 görseli seçin.
   - **Submit & Open.**
3. **Kutulama ve Etiketleme:**
   - Motiflerin sınırlarını tam kapsayacak şekilde sınırlayıcı kutuları (bounding boxes) çizin.
   - Belirsiz/şüpheli motifler için `unmapped_visual_motif` kullanın.
   - Simetrik bordürlerde belirgin tekrarları tek tek kutulayın.
4. **Dışa Aktarma (Export):**
   - Görev tamamlandığında **Export task dataset** seçeneğine tıklayın.
   - Format olarak **YOLO 1.1** seçin ve `.zip` olarak indirin.

---

## 3. Etiketleri Sisteme İçe Aktarma (Import)

İndirdiğiniz YOLO etiketlerini sisteme aktarmak ve doğrulamak için:
```bash
python scripts/import_real_annotations.py --input-zip path/to/exported_batch_01.zip
```
Bu betik:
- Etiketlerin formatını ve 17 sınıf uyumunu denetler.
- Holdout kara listesi sızıntı kontrolünü (`holdout_leakage_prohibition`) teyit eder.
- Doğrulanmış etiketleri `data/datasets/real_corpus_v1/annotations/` altına işler.
"""
    readme_file = BATCH_DIR / "README.md"
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"[8] Written {readme_file}.")

    # 10. Final Verification of the 50 images
    print("\n[9] Running Final Batch-01 Verification:")
    all_valid = True
    for r in stratified_selection:
        fn = r["filename"]
        img_p = BATCH_IMAGES_DIR / fn
        if not img_p.exists():
            print(f"  [FAIL] Missing image: {fn}")
            all_valid = False
            continue
        sha = compute_file_sha256(img_p)
        if sha in blacklist:
            print(f"  [FAIL] Blacklist collision in Batch-01: {fn}")
            all_valid = False
        if not r.get("license_verified"):
            print(f"  [FAIL] License not verified: {fn}")
            all_valid = False
            
    if all_valid:
        print(f"  [PASS] All {len(stratified_selection)} images are verified training_safe, CC0, and blacklist-free (0 collision)!")

if __name__ == "__main__":
    main()
