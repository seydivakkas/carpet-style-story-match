"""
COCO 1.0 Dataset Exporter for Synthetic Motifs.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from packages.synthetic_motifs.annotations import SyntheticCarpetSample


class CocoExporter:
    """Exports dataset samples to standard COCO 1.0 format."""

    @staticmethod
    def export(
        samples: List[SyntheticCarpetSample],
        class_map: Dict[str, int],
        output_path: Path,
        split_name: str = "train",
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        categories = [
            {"id": cid, "name": key, "supercategory": "motif"}
            for key, cid in sorted(class_map.items(), key=lambda x: x[1])
        ]

        images = []
        annotations = []
        ann_id = 1

        for img_idx, sample in enumerate(samples, start=1):
            images.append({
                "id": img_idx,
                "file_name": Path(sample.image_ref).name,
                "width": sample.image_width,
                "height": sample.image_height,
                "sample_id": sample.sample_id,
                "seed": sample.seed,
            })

            for inst in sample.instances:
                if inst.ignore:
                    continue
                cat_id = class_map.get(inst.visual_candidate_key, 0)
                
                # COCO bbox format: [xmin, ymin, width, height]
                xmin, ymin, xmax, ymax = inst.bbox_xyxy
                bw = max(0.0, xmax - xmin)
                bh = max(0.0, ymax - ymin)
                area = bw * bh

                # Segmentation polygon
                flat_poly = []
                for p in inst.polygon:
                    flat_poly.extend([float(p[0]), float(p[1])])

                # OBB
                flat_obb = []
                for p in inst.obb:
                    flat_obb.extend([float(p[0]), float(p[1])])

                annotations.append({
                    "id": ann_id,
                    "image_id": img_idx,
                    "category_id": cat_id,
                    "bbox": [float(xmin), float(ymin), float(bw), float(bh)],
                    "area": float(area),
                    "segmentation": [flat_poly] if len(flat_poly) >= 6 else [],
                    "obb": flat_obb,
                    "iscrowd": 0,
                    "instance_id": inst.instance_id,
                    "visible_fraction": inst.visible_fraction,
                })
                ann_id += 1

        coco_data = {
            "info": {
                "description": f"Synthetic Motif Dataset — {split_name} split",
                "version": "1.0.0",
                "year": 2026,
            },
            "licenses": [{"id": 1, "name": "All Rights Reserved", "url": "https://github.com/seydivakkas"}],
            "images": images,
            "annotations": annotations,
            "categories": categories,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(coco_data, f, indent=2)

        return output_path
