"""Gerçek model dosyası kaynağına dokunmayan, küçük ve sentetik aktarım testleri."""
import hashlib
import json
import pytest
from scripts.stage_motif_evidence import stage, safe_relative
from scripts.motif_evidence_audit import audit

def test_stage_dry_run_then_apply_and_repeat(tmp_path, monkeypatch):
    root = tmp_path / "source"
    dest = tmp_path / "destination"
    root.mkdir()
    dest.mkdir()
    payload = b"truth-preserving fixture"
    p = root / "weights.bin"
    p.write_bytes(payload)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"artifacts":[{"name":"test", "path":"weights.bin",
        "size_bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest()}]}),encoding="utf-8")
    assert stage(manifest, root, dest, apply=False)[0]["state"] == "READY_TO_COPY"
    assert not (dest / "weights.bin").exists()
    assert stage(manifest, root, dest, apply=True)[0]["state"] == "COPIED"
    assert stage(manifest, root, dest, apply=True)[0]["state"] == "ALREADY_IDENTICAL"

def test_no_mismatching_model_hash_can_be_staged(tmp_path):
    src=tmp_path/"source"
    dst=tmp_path/"target"
    src.mkdir(); dst.mkdir()
    (src/"data.bin").write_bytes(b"not-the-original")
    manifest=tmp_path/"m.json"
    manifest.write_text(json.dumps({"artifacts":[{"name":"checkpoint","path":"data.bin","sha256":"0"*64}]}))
    assert stage(manifest,src,dst,apply=True)[0]["state"]=="HASH_MISMATCH"
    assert not (dst/"data.bin").exists()

def test_rejects_path_traversal():
    with pytest.raises(ValueError):
        safe_relative("../private/secret.json")
