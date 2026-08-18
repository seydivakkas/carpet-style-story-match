"""
Canonical JSON Dataset Exporter.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import json
from pathlib import Path
from packages.synthetic_motifs.annotations import SyntheticCarpetSample


class CanonicalJsonExporter:
    """Exports source-of-truth SyntheticCarpetSample Pydantic instances to JSON."""

    @staticmethod
    def export(sample: SyntheticCarpetSample, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(sample.model_dump_json(indent=2))
        return output_path
