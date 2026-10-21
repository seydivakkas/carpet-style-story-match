"""Yerel motif veri/model kanıtlarının hash ve yol bütünlüğünü inceler.

Gerçek dosya yoksa veri sentezlemez ve PASS raporu üretmez.
Çıkış kodu: 0 (yalnız envanter), 2 (--strict, eksik veya hash hatalı).
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "manifests" / "motif_artifact_requirements.json"

def audit(manifest_path: Path) -> dict:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = []
    for item in data["artifacts"]:
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"Yalnızca depo göreli yollar desteklenir: {rel}")
        file = (ROOT / rel).resolve()
        if not file.is_relative_to(ROOT):
            raise ValueError(f"Depo dışına çıkış: {rel}")
        expected = item.get("sha256")
        if not file.is_file():
            entries.append({"name": item["name"], "path": str(rel), "status": "MISSING", "sha256": None})
            continue
        with file.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        actual_size = file.stat().st_size
        expected_size = item.get("size_bytes")
        if expected_size is not None and actual_size != expected_size:
            state = "SIZE_MISMATCH"
        elif expected and expected.lower() != digest:
            state = "HASH_MISMATCH"
        elif not expected:
            state = "PRESENT_UNVERIFIED"
        else:
            state = "VERIFIED"
        entries.append({"name": item["name"], "path": str(rel), "status": state,
                        "sha256": digest, "bytes": actual_size})
    all_present = all(e["status"] != "MISSING" for e in entries)
    complete = all(e["status"] == "VERIFIED" for e in entries)
    return {"schema": "motif-evidence-audit-v2", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "acceptance": "FILES_VERIFIED_MODEL_NOT_ACCEPTED" if complete else "HOLD_MISSING_OR_UNVERIFIED_EVIDENCE",
            "all_present": all_present, "all_verified": complete,
            "counts": {k: sum(e["status"] == k for e in entries) for k in
                       ("MISSING", "SIZE_MISMATCH", "HASH_MISMATCH", "PRESENT_UNVERIFIED", "VERIFIED")},
            "entries": entries}

def main() -> int:
    parser = argparse.ArgumentParser(description="Gerçek motif veri/model kanıt envanteri")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Kanıt eksikse çıkış kodu 2")
    args = parser.parse_args()
    result = audit(args.manifest)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 2 if args.strict and not result["all_verified"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
