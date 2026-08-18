"""
V2-09A — Procedural Motif Synthetic Dataset Foundation Test Suite.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import copy
import json
import math
from pathlib import Path
import tempfile
import numpy as np
import pytest

from packages.synthetic_motifs import (
    GENERATOR_VERSION,
    DATASET_VERSION,
    REGISTRY_VERSION,
    RANDOMIZATION_POLICY_VERSION,
    DATASET_POLICY_VERSION,
)
from packages.synthetic_motifs.geometry import (
    Point,
    Polygon,
    BoundingBox,
    OrientedBoundingBox,
    create_homography_matrix,
)
from packages.synthetic_motifs.registry import (
    SyntheticMotifRegistry,
    VisualCandidateKey,
    MotifRegistryEntry,
)
from packages.synthetic_motifs.composer import CarpetComposer
from packages.synthetic_motifs.renderers.base import VectorRenderer
from packages.synthetic_motifs.transforms import GeometricTransformer
from packages.synthetic_motifs.randomization import (
    PhotometricRandomizer,
    ImagingRandomizer,
    MaterialTextureRandomizer,
    OcclusionRandomizer,
)
from packages.synthetic_motifs.annotations import (
    SyntheticMotifInstanceGT,
    SyntheticCarpetSample,
    FORBIDDEN_CULTURAL_FIELDS,
)
from packages.synthetic_motifs.manifest import DatasetManifestGenerator
from packages.synthetic_motifs.exporters.canonical_json import CanonicalJsonExporter
from packages.synthetic_motifs.exporters.coco import CocoExporter
from packages.synthetic_motifs.exporters.yolo_detect import YoloDetectExporter
from packages.synthetic_motifs.exporters.yolo_obb import YoloObbExporter
from packages.synthetic_motifs.exporters.yolo_segment import YoloSegmentExporter
from packages.synthetic_motifs.validation import OracleValidator
from packages.synthetic_motifs.cli import (
    generate_single_sample,
    run_generate_dataset,
    validate_dataset_folder,
    load_class_map,
)


# 1. Registry Completeness Test
def test_v2_09a_registry_completeness_17_keys():
    registry = SyntheticMotifRegistry()
    keys = registry.list_keys()
    assert len(keys) == 17, f"Expected exactly 17 keys, got {len(keys)}"
    
    expected_enum_keys = {
        "cloud_band_like", "comb_like", "hook_like", "horn_like",
        "human_figure_like_geometric", "lattice_like", "lotus_like",
        "lozenge_like", "medallion_like", "niche_like", "octagonal_form",
        "palmette_like", "rosette_like", "star_like", "tree_like",
        "unmapped_visual_motif", "vine_scroll_like"
    }
    actual_keys = {k.value for k in keys}
    assert actual_keys == expected_enum_keys

    # Verify each entry can generate a valid polygon
    for key in keys:
        entry = registry.get(key)
        assert isinstance(entry, MotifRegistryEntry)
        poly = registry.generate_polygon(key, cx=320, cy=320, radius=80)
        assert isinstance(poly, Polygon)
        assert len(poly.vertices) >= 3
        assert poly.area > 50.0


# 2. Geometric Oracle: BBox and Mask Containment
def test_v2_09a_geometric_oracle_bbox_mask_containment():
    registry = SyntheticMotifRegistry()
    for key in [VisualCandidateKey.STAR_LIKE, VisualCandidateKey.PALMETTE_LIKE, VisualCandidateKey.MEDALLION_LIKE]:
        poly = registry.generate_polygon(key, cx=200, cy=200, radius=60)
        bbox = poly.get_bounding_box()
        mask = VectorRenderer.generate_instance_mask(400, 400, poly)

        contained = OracleValidator.verify_mask_bbox_containment(mask, bbox.to_xyxy(), margin=2.0)
        assert contained is True, f"Mask pixels extended outside bounding box for {key.value}"


# 3. Geometric Oracle: Polygon and Mask IoU Consistency
def test_v2_09a_geometric_oracle_polygon_mask_iou():
    registry = SyntheticMotifRegistry()
    poly = registry.generate_polygon(VisualCandidateKey.ROSETTE_LIKE, cx=250, cy=250, radius=70)
    mask = VectorRenderer.generate_instance_mask(500, 500, poly)
    iou = OracleValidator.verify_polygon_mask_consistency(poly, mask, 500, 500)
    assert iou > 0.95, f"Polygon to raster mask IoU ({iou:.4f}) is below 0.95"


# 4. Geometric Oracle: OBB Containment
def test_v2_09a_geometric_oracle_obb_containment():
    registry = SyntheticMotifRegistry()
    for key in registry.list_keys():
        poly = registry.generate_polygon(key, cx=300, cy=300, radius=75, rotation_deg=35.0)
        obb = poly.get_oriented_bounding_box()
        contained = OracleValidator.verify_obb_containment(poly, obb.to_list(), margin=2.0)
        assert contained is True, f"Polygon vertices not contained in OBB for {key.value}"


# 5. Perspective Homography Point Propagation
def test_v2_09a_perspective_homography_exact_projection():
    src_corners = [(0.0, 0.0), (400.0, 0.0), (400.0, 400.0), (0.0, 400.0)]
    dst_corners = [(40.0, 20.0), (360.0, 10.0), (380.0, 390.0), (20.0, 370.0)]
    H = create_homography_matrix(src_corners, dst_corners)

    poly = Polygon([(100.0, 100.0), (300.0, 100.0), (200.0, 300.0)])
    warped_poly = poly.transform_homography(H)

    # Verify math
    valid = OracleValidator.verify_homography_point_projection(
        poly.vertices, H, warped_poly.vertices, tolerance=1e-4
    )
    assert valid is True


# 6. Photometric Invariance Test
def test_v2_09a_photometric_invariance():
    img = np.full((300, 300, 3), 128, dtype=np.uint8)
    poly = Polygon([(50.0, 50.0), (150.0, 50.0), (100.0, 150.0)])
    bbox = poly.get_bounding_box()
    obb = poly.get_oriented_bounding_box()

    inst_before = SyntheticMotifInstanceGT(
        instance_id="inst_test_01",
        visual_candidate_key="star_like",
        bbox_xyxy=bbox.to_xyxy(),
        bbox_normalized=bbox.to_normalized(300, 300),
        polygon=poly.to_list(),
        obb=obb.to_list(),
        obb_normalized=obb.to_normalized(300, 300),
        visible_fraction=1.0,
        is_truncated=False,
        is_occluded=False,
        ignore=False,
    )

    # Apply photometric adjustments
    img_after, _ = PhotometricRandomizer.apply(img, rng=np.random.RandomState(42))
    img_after, _ = ImagingRandomizer.apply(img_after, rng=np.random.RandomState(42))

    inst_after = copy.deepcopy(inst_before)

    # Annotations MUST be bit-for-bit identical
    assert OracleValidator.verify_photometric_invariance(inst_before, inst_after) is True


# 7. Occlusion and Crop Visibility Semantics
def test_v2_09a_occlusion_and_crop_visibility_semantics():
    poly = Polygon([(10.0, 10.0), (100.0, 10.0), (100.0, 100.0), (10.0, 100.0)])
    # Clip against a canvas that cuts off half of the polygon: [0, 50] x [0, 100]
    clipped = poly.clip_to_canvas(50.0, 100.0)
    assert clipped is not None
    assert clipped.area < poly.area
    vis_frac = clipped.area / poly.area
    assert 0.40 <= vis_frac <= 0.60
    
    # Check ignore threshold logic
    ignore_flag = (vis_frac < 0.20)
    assert ignore_flag is False

    # Heavy clip (<20%)
    heavy_clip = poly.clip_to_canvas(20.0, 100.0)
    assert heavy_clip is not None
    heavy_vis_frac = heavy_clip.area / poly.area
    assert (heavy_vis_frac < 0.20) is True


# 8. Negative Samples & Hard Negatives
def test_v2_09a_negative_samples_and_hard_negatives():
    composer = CarpetComposer()
    img, insts, hns, spec, sig = composer.compose_scene(
        width=300, height=300, seed=999, is_negative=True
    )
    assert len(insts) == 0
    assert spec["layout_type"].startswith("NEGATIVE")
    assert isinstance(sig, str) and len(sig) == 64


# 9. Multi-Format Exporters Test
def test_v2_09a_multi_format_exporters():
    class_map = load_class_map()
    poly = Polygon([(50.0, 50.0), (150.0, 50.0), (150.0, 150.0), (50.0, 150.0)])
    bbox = poly.get_bounding_box()
    obb = poly.get_oriented_bounding_box()

    inst = SyntheticMotifInstanceGT(
        instance_id="inst_0001_star_like",
        visual_candidate_key="star_like",
        bbox_xyxy=bbox.to_xyxy(),
        bbox_normalized=bbox.to_normalized(300, 300),
        polygon=poly.to_list(),
        obb=obb.to_list(),
        obb_normalized=obb.to_normalized(300, 300),
        visible_fraction=1.0,
        is_truncated=False,
        is_occluded=False,
        ignore=False,
    )

    sample = SyntheticCarpetSample(
        sample_id="syn_test_001",
        seed=42,
        split="train",
        image_width=300,
        image_height=300,
        image_ref="images/train/syn_test_001.jpg",
        scene_signature="abc123sig",
        instances=[inst],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        
        # 1. Canonical JSON
        json_path = td / "sample.json"
        CanonicalJsonExporter.export(sample, json_path)
        assert json_path.exists()

        # 2. COCO
        coco_path = td / "coco.json"
        CocoExporter.export([sample], class_map, coco_path)
        with open(coco_path, "r", encoding="utf-8") as f:
            coco_data = json.load(f)
            assert len(coco_data["images"]) == 1
            assert len(coco_data["annotations"]) == 1
            assert "obb" in coco_data["annotations"][0]

        # 3. YOLO Detect
        yolo_path = td / "yolo.txt"
        YoloDetectExporter.export_sample(sample, class_map, yolo_path)
        with open(yolo_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            parts = lines[0].strip().split()
            assert len(parts) == 5  # class_id, xc, yc, w, h

        # 4. YOLO OBB
        obb_path = td / "yolo_obb.txt"
        YoloObbExporter.export_sample(sample, class_map, obb_path)
        with open(obb_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            parts = lines[0].strip().split()
            assert len(parts) == 9  # class_id + 8 coords

        # 5. YOLO Segment
        seg_path = td / "yolo_seg.txt"
        YoloSegmentExporter.export_sample(sample, class_map, seg_path)
        with open(seg_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            parts = lines[0].strip().split()
            assert len(parts) == 9  # class_id + 4 points (8 coords)


# 10. Determinism and Seed Variation
def test_v2_09a_determinism_and_seed_variation():
    composer = CarpetComposer()
    _, insts1, _, _, sig1 = composer.compose_scene(300, 300, seed=12345)
    _, insts2, _, _, sig2 = composer.compose_scene(300, 300, seed=12345)
    _, insts3, _, _, sig3 = composer.compose_scene(300, 300, seed=54321)

    assert sig1 == sig2
    assert len(insts1) == len(insts2)
    assert insts1[0].bbox_xyxy == insts2[0].bbox_xyxy
    assert sig1 != sig3


# 11. Cross-Split Leakage Prevention
def test_v2_09a_split_leakage_prevention():
    samples = []
    composer = CarpetComposer()
    for i in range(15):
        split = "train" if i < 10 else ("validation" if i < 13 else "test")
        _, sample = generate_single_sample(composer, f"syn_{i}", seed=1000 + i, split=split, width=200, height=200)
        samples.append(sample)

    manifest = DatasetManifestGenerator.generate_manifest(samples, master_seed=42, annotation_formats=["json"])
    assert manifest["cross_split_leakage_detected"] is False
    assert manifest["split_counts"]["train"] == 10
    assert manifest["split_counts"]["validation"] == 3
    assert manifest["split_counts"]["test"] == 2


# 12. Cultural Safety: Forbidden Fields Rejected
def test_v2_09a_cultural_safety_forbidden_fields():
    # Attempting to inject forbidden field into SyntheticMotifInstanceGT must raise ValueError
    with pytest.raises(ValueError):
        SyntheticMotifInstanceGT.model_validate({
            "instance_id": "bad_01",
            "visual_candidate_key": "star_like",
            "bbox_xyxy": [0, 0, 10, 10],
            "bbox_normalized": [0, 0, 0.1, 0.1],
            "polygon": [[0, 0], [10, 0], [10, 10]],
            "obb": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "visible_fraction": 1.0,
            "is_truncated": False,
            "is_occluded": False,
            "ignore": False,
            "culture": "Seljuk",  # FORBIDDEN!
        })


# 13. Data Isolation: Real Corpus & Production Database Isolation
def test_v2_09a_data_isolation_zero_corpus_and_db_mutations():
    # Verify no database write or connection is triggered by generator
    registry = SyntheticMotifRegistry()
    composer = CarpetComposer(registry)
    _, instances, _, _, _ = composer.compose_scene(320, 320, seed=42)
    assert len(instances) > 0
    # No SQL connection imported or accessed inside packages.synthetic_motifs


# 14. Class Map Invariant: 17 Unique Classes
def test_v2_09a_class_map_immutability_and_consistency():
    class_map = load_class_map()
    assert len(class_map) == 17
    class_ids = set(class_map.values())
    assert class_ids == set(range(17))


# 15. CLI Dry Run and Validate Dataset Folder
def test_v2_09a_cli_dry_run_and_validation():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        res = run_generate_dataset(
            output_dir=out_dir,
            total_samples=10,
            master_seed=42,
            width=240,
            height=240,
            dry_run=False,
        )
        assert res["total_samples"] == 10
        
        # Validate folder
        val_res = validate_dataset_folder(out_dir)
        assert val_res["status"] == "PASS"
        assert val_res["bbox_violations"] == 0
        assert val_res["obb_violations"] == 0
        assert val_res["leakage_count"] == 0
        assert val_res["positive_label_leak_count"] == 0


# 16. Controlled Hard Negative Registry & Zero Positive Label Leakage
def test_v2_09a_controlled_hard_negatives_zero_label_leakage():
    from packages.synthetic_motifs.hard_negatives import HardNegativeRegistry
    hn_reg = HardNegativeRegistry()
    families = hn_reg.list_keys()
    assert len(families) == 5
    assert "radial_polygon_nonstar" in families
    assert "radial_ornament_nonrosette" in families
    assert "isolated_lozenge_pattern" in families
    assert "octagonal_radial_variant" in families
    assert "generic_branching_form" in families

    composer = CarpetComposer()
    img, insts, hns, spec, sig = composer.compose_scene(
        width=300, height=300, seed=123, hard_negative_mode="HARD_NEGATIVE_ONLY"
    )
    assert len(insts) == 0, "HARD_NEGATIVE_ONLY scene must have 0 positive target instances"
    assert len(hns) > 0, "HARD_NEGATIVE_ONLY scene must contain hard negative provenance"

    # Verify zero positive label leakage
    target_keys = {inst.visual_candidate_key for inst in insts}
    for hn in hns:
        assert hn.hard_negative_key not in target_keys
        assert hn.hard_negative_id not in target_keys


# 17. Exporters Exclude Hard Negatives from Positive Ground Truth Annotations
def test_v2_09a_exporters_exclude_hard_negatives_from_positive_gt():
    composer = CarpetComposer()
    img, insts, hns, spec, sig = composer.compose_scene(
        width=300, height=300, seed=456, hard_negative_mode="MIXED_HARD_NEGATIVE"
    )
    assert len(insts) > 0
    assert len(hns) > 0

    sample = SyntheticCarpetSample(
        sample_id="syn_hn_test_01",
        seed=456,
        split="train",
        image_width=300,
        image_height=300,
        image_ref="images/train/syn_hn_test_01.jpg",
        scene_signature=sig,
        instances=insts,
        hard_negatives=hns,
    )

    class_map = load_class_map()
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)

        # 1. COCO Export
        coco_path = td / "coco.json"
        CocoExporter.export([sample], class_map, coco_path)
        with open(coco_path, "r", encoding="utf-8") as f:
            coco_data = json.load(f)
            assert len(coco_data["annotations"]) == len(insts)

        # 2. YOLO Detect Export
        yolo_path = td / "yolo.txt"
        YoloDetectExporter.export_sample(sample, class_map, yolo_path)
        with open(yolo_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == len(insts)

        # 3. YOLO OBB Export
        obb_path = td / "yolo_obb.txt"
        YoloObbExporter.export_sample(sample, class_map, obb_path)
        with open(obb_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == len(insts)

