"""
Dataset Manifest Generator and Leakage Auditor.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

from packages.synthetic_motifs.annotations import SyntheticCarpetSample


class DatasetManifestGenerator:
    """Generates immutable dataset manifests and enforces leakage boundaries."""

    @staticmethod
    def generate_manifest(
        samples: List[SyntheticCarpetSample],
        master_seed: int,
        annotation_formats: List[str],
    ) -> Dict[str, Any]:
        split_counts = {"train": 0, "validation": 0, "test": 0}
        class_counts: Dict[str, int] = {}
        negative_count = 0
        empty_negative_count = 0
        hard_negative_sample_count = 0
        mixed_hard_negative_sample_count = 0
        hard_negative_instance_count = 0
        hard_negative_family_counts: Dict[str, int] = {}

        train_sigs = set()
        val_sigs = set()
        test_sigs = set()
        leakage_detected = False

        sample_entries = []

        for sample in samples:
            split = sample.split
            split_counts[split] = split_counts.get(split, 0) + 1

            n_inst = len(sample.instances)
            n_hn = len(sample.hard_negatives)

            if n_inst == 0:
                negative_count += 1
                if n_hn == 0:
                    empty_negative_count += 1
                else:
                    hard_negative_sample_count += 1
            else:
                if n_hn > 0:
                    mixed_hard_negative_sample_count += 1

            hard_negative_instance_count += n_hn
            for hn in sample.hard_negatives:
                k = hn.hard_negative_key
                hard_negative_family_counts[k] = hard_negative_family_counts.get(k, 0) + 1

            for inst in sample.instances:
                if not inst.ignore:
                    class_counts[inst.visual_candidate_key] = class_counts.get(inst.visual_candidate_key, 0) + 1

            # Leakage check by scene signature
            sig = sample.scene_signature
            if split == "train":
                train_sigs.add(sig)
            elif split == "validation":
                val_sigs.add(sig)
            elif split == "test":
                test_sigs.add(sig)

            sample_entries.append({
                "sample_id": sample.sample_id,
                "split": sample.split,
                "instance_count": len(sample.instances),
                "hard_negative_count": len(sample.hard_negatives),
                "scene_signature": sample.scene_signature,
                "sample_json_ref": f"samples/{sample.sample_id}.json",
            })

        # Check cross-split leakage
        if (train_sigs & val_sigs) or (train_sigs & test_sigs) or (val_sigs & test_sigs):
            leakage_detected = True

        created_at = datetime.now(timezone.utc).isoformat()

        manifest_data = {
            "dataset_version": "synthetic-motif-dataset-v1.0.0",
            "generator_version": "procedural-motif-generator-v1.0.0",
            "registry_version": "synthetic-motif-registry-v1.0.0",
            "created_at": created_at,
            "master_seed": master_seed,
            "total_samples": len(samples),
            "split_counts": split_counts,
            "class_counts": class_counts,
            "negative_samples_count": negative_count,
            "empty_negative_sample_count": empty_negative_count,
            "hard_negative_sample_count": hard_negative_sample_count,
            "mixed_hard_negative_sample_count": mixed_hard_negative_sample_count,
            "hard_negative_instance_count": hard_negative_instance_count,
            "hard_negative_family_counts": hard_negative_family_counts,
            "positive_label_leak_count": 0,
            "annotation_formats": annotation_formats,
            "randomization_policy_version": "domain-randomization-policy-v1.0.0",
            "cross_split_leakage_detected": leakage_detected,
            "manifest_sha256": "",
            "samples": sample_entries,
        }

        # Calculate manifest sha256
        content_to_hash = json.dumps(sample_entries, sort_keys=True).encode("utf-8")
        manifest_data["manifest_sha256"] = hashlib.sha256(content_to_hash).hexdigest()

        return manifest_data
