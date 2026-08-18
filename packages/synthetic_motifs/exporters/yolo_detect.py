"""
YOLO Detect Format Exporter.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from pathlib import Path
from typing import Dict
from packages.synthetic_motifs.annotations import SyntheticCarpetSample


class YoloDetectExporter:
    """Exports normalized YOLO bounding boxes: <class_id> <xc> <yc> <w> <h>."""

    @staticmethod
    def export_sample(sample: SyntheticCarpetSample, class_map: Dict[str, int], output_txt_path: Path) -> Path:
        output_txt_path.parent.mkdir(parents=True, exist_ok=True)
        lines = []

        w = float(sample.image_width)
        h = float(sample.image_height)

        for inst in sample.instances:
            if inst.ignore:
                continue
            cat_id = class_map.get(inst.visual_candidate_key, 0)
            xmin, ymin, xmax, ymax = inst.bbox_xyxy
            bw = max(0.0, xmax - xmin) / w
            bh = max(0.0, ymax - ymin) / h
            xc = (xmin / w) + (bw / 2.0)
            yc = (ymin / h) + (bh / 2.0)
            
            lines.append(f"{cat_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")

        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))

        return output_txt_path
