"""Gerçek motif ve VLM kanıt envanteri; üretim model onayı verilmez.

Sabit liste yerine repo'da tanımlı SHA/byte beklenen kanıt manifesti kullanılır.
HTTP yanıtında yerel yollar, gizli anahtar veya model ağırlık verisi yayımlanmaz.
"""
import json
import os
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/system", tags=["system-acceptance"])
SOURCE_ROOT = Path(__file__).resolve().parents[5]
CONTAINER_ROOT = Path(__file__).resolve().parents[3]

def _manifest_path() -> Path:
    # Kaynak depo ile çalışma zamanı Docker imajında aynı resmi manifest.
    for root in (SOURCE_ROOT, CONTAINER_ROOT):
        candidate = root / "docs/manifests/motif_artifact_requirements.json"
        if candidate.is_file():
            return candidate
    raise RuntimeError("Gerçek motif kabul manifesti paketlenmemiş.")

def _source_root() -> Path:
    if (_manifest_path().is_relative_to(CONTAINER_ROOT)):
        return CONTAINER_ROOT
    return SOURCE_ROOT

class AcceptanceResponse(BaseModel):
    status: str
    model_quality: str
    approved_for_production: bool
    independent_holdout_verified: bool
    missing_artifacts: list[str]
    checked_artifacts: int
    available_artifacts: int
    caution_tr: str

def audit_runtime_evidence(root: Path) -> AcceptanceResponse:
    manifest = json.loads(_manifest_path().read_text(encoding="utf-8"))
    items = manifest.get("artifacts")
    if not isinstance(items, list) or not items:
        raise RuntimeError("Gerçek motif kabul manifesti boş/geçersiz.")
    resolved_root = root.resolve()
    checked = len(items)
    available = 0
    missing = []
    for i, entry in enumerate(items):
        rel = Path(entry["path"])
        target = (resolved_root / rel).resolve()
        if rel.is_absolute() or ".." in rel.parts or not target.is_relative_to(resolved_root):
            raise RuntimeError("Manifestte güvenli olmayan yol.")
        # Büyük model ağırlıklarının SHA-256 denetimi HTTP yanıtında
        # çalıştırılmaz. Yalnız varlık raporlanır, bilimsel kabul her durumda HOLD.
        if target.is_file():
            available += 1
        else:
            # Yol veya özel model dosya isimleri istemciye sızdırılmaz.
            missing.append(f"kanit_{i+1:02d}")
    return AcceptanceResponse(
        status="HOLD", model_quality="NOT_VALIDATED",
        approved_for_production=False, independent_holdout_verified=False,
        missing_artifacts=missing, checked_artifacts=checked,
        available_artifacts=available,
        caution_tr=(
            "Motif ve görsel doğrulayıcılar üretim onayı almadı. "
            "Eksik veya yalnızca mevcut görünen dosyalar model başarısı sayılmaz. "
            "SHA-256 ve bağımsız holdout doğrulaması ayrıca zorunludur."
        ),
    )

@router.get("/model-acceptance", response_model=AcceptanceResponse)
def model_acceptance() -> AcceptanceResponse:
    custom_root = os.environ.get("CARPET_EVIDENCE_ROOT")
    return audit_runtime_evidence(Path(custom_root) if custom_root else _source_root())
