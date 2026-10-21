"""Gerçek veri ve ağırlıkları Windows/Linux yerel arşivinden güvenli biçimde sahnele.

Kaynak kullanıcı tarafından sağlanır; içerik üretilmez ve GitHub'a yüklenmez.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO / "docs/manifests/motif_artifact_requirements.json"

def safe_relative(value: str) -> Path:
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("Yalnızca güvenli göreli dosya yolu desteklenir.")
    return rel

def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()

def stage(manifest_path: Path, source_root: Path, destination_root: Path, *, apply: bool) -> list[dict]:
    sources = source_root.resolve(strict=True)
    target_root = destination_root.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs = []
    for item in manifest["artifacts"]:
        rel = safe_relative(item["path"])
        source = (sources / rel).resolve()
        target = (target_root / rel).resolve()
        if not source.is_relative_to(sources) or not target.is_relative_to(target_root):
            raise ValueError("Sembolik bağlantı depo veya kaynak kökünün dışına çıkıyor.")
        if not source.is_file():
            outputs.append({"path": str(rel), "state": "SOURCE_MISSING"})
            continue
        length = source.stat().st_size
        digest = digest_file(source)
        if item.get("size_bytes") is not None and length != item["size_bytes"]:
            outputs.append({"path": str(rel), "state": "SIZE_MISMATCH"})
            continue
        if item.get("sha256") and item["sha256"].lower() != digest:
            outputs.append({"path": str(rel), "state": "HASH_MISMATCH"})
            continue
        if target.is_file():
            if digest_file(target) == digest:
                outputs.append({"path": str(rel), "state": "ALREADY_IDENTICAL", "sha256": digest})
                continue
            outputs.append({"path": str(rel), "state": "TARGET_CONFLICT"})
            continue
        if not apply:
            outputs.append({"path": str(rel), "state": "READY_TO_COPY", "sha256": digest, "bytes": length})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        # Dosya önce aynı diskte geçici konuma kopyalanır; başarısız kopyada hedef oluşmaz.
        temp = target.with_name(target.name + "." + uuid.uuid4().hex + ".part")
        try:
            with source.open("rb") as reader, temp.open("xb") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
            if temp.stat().st_size != length or digest_file(temp) != digest:
                raise ValueError("Kaynak ve kopya SHA-256 bütünlüğü uyuşmadı.")
            if target.exists():
                raise FileExistsError("Kopyalama sırasında hedef dosya oluşturulmuş.")
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)
        outputs.append({"path": str(rel), "state": "COPIED", "sha256": digest, "bytes": length})
    return outputs

def main() -> int:
    parser = argparse.ArgumentParser(description="Gerçek motif kanıtlarını yerel klasörden SHA doğrulamalı taşı")
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--destination-root", type=Path, default=REPO)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--apply", action="store_true", help="Dosyaları gerçekten kopyala; varsayılan yalnız ön kontroldür")
    opts = parser.parse_args()
    try:
        entries = stage(opts.manifest, opts.source_root, opts.destination_root, apply=opts.apply)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Kanıt dosyası işlenemedi: {exc}", file=sys.stderr)
        return 2
    for entry in entries:
        print(json.dumps(entry, ensure_ascii=False))
    print("NOT: Dosyaların mevcut olması model doğruluk veya veri kullanım izni kanıtı DEĞİLDİR.")
    return 0 if all(x["state"] in ("COPIED", "ALREADY_IDENTICAL") for x in entries) else 2

if __name__ == "__main__":
    raise SystemExit(main())
