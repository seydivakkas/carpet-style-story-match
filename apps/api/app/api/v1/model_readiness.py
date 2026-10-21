"""Gerçek motif modelinin üretim kabul kanıtı durumunu açıkça gösterir.

Dosya varlığı doğruluk/mAP kanıtı sayılmaz. Dosya yolları ve sistem sırları
HTTP yanıtına dahil edilmez. Kabul edilmiş bağımsız holdout olmadan HOLD.
"""
import os
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/system", tags=["system-acceptance"])
# Proje kökü geliştirme ortamında geçerli; container ortamında mount ayrı olabilir.
PROJECT_ROOT = Path(__file__).resolve().parents[5]
EVIDENCE_FILES = {
    "catalog_sqlite": "apps/api/carpet_db.sqlite",
    "raw_detect_records": "artifacts/v2-09-final/catalog-batch/detect-raw-proposals.json",
    "raw_obb_records": "artifacts/v2-09-final/catalog-batch/obb-raw-proposals.json",
    "detector_license": "data/detectors/ultralytics-license-review-v1.json",
    "detector_policy": "data/detectors/detector-baseline-policy-v1.json",
    "real_motif_manifest": "data/datasets/real-motif-benchmark-v1/manifest.json",
    "detect_experiment": "data/detectors/v2-09b-yolo11n-detect-seed42-manifest.json",
    "obb_experiment": "data/detectors/v2-09b-yolo11n-obb-seed42-manifest.json",
    "r0_model": "artifacts/v2-09c/models/R0",
}

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
    # İsteği gönderen istemci yerel yolları göremez; sadece envanter anahtarları.
    available = {key: (root / rel).exists() for key, rel in EVIDENCE_FILES.items()}
    missing = sorted(key for key, present in available.items() if not present)
    return AcceptanceResponse(
        status="HOLD",
        model_quality="NOT_VALIDATED",
        approved_for_production=False,
        independent_holdout_verified=False,
        missing_artifacts=missing,
        checked_artifacts=len(available),
        available_artifacts=sum(available.values()),
        caution_tr=(
            "Gerçek motif dedektörü üretim doğrulamasını geçmedi. "
            "Eksik deney verileri ve model dosyaları tamamlanmadan "
            "motif sonuçları kesin bulgu olarak sunulmamalıdır."
        ),
    )

@router.get("/model-acceptance", response_model=AcceptanceResponse)
def model_acceptance() -> AcceptanceResponse:
    custom_root = os.environ.get("CARPET_EVIDENCE_ROOT")
    return audit_runtime_evidence(Path(custom_root).resolve() if custom_root else PROJECT_ROOT)
