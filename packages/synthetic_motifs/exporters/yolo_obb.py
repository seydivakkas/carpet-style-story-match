"""
YOLO Oriented Bounding Box (OBB) Format Exporter.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from pathlib import Path
from typing import Dict
import numpy as np

from packages.synthetic_motifs.annotations import SyntheticCarpetSample


class YoloObbExporter:
    """Exports Ultralytics-compatible 8-point normalized OBBs: <class_id> <x1> <y1> <x2> <y2> <x3> <y3> <x4> <y4>."""

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
            
            # 4 corners
            coords_str = []
            for pt in inst.obb:
                nx = np.clip(pt[0] / w, 0.0, 1.0)
                ny = np.clip(pt[1] / h, 0.0, 1.0)
                coords_str.append(f"{nx:.6f} {ny:.6f}")
            
            line = f"{cat_id} " + " ".join(coords_str)
            lines.append(line)

        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))

        return output_txt_path
