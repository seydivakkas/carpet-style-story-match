"""
YOLO11n Motif Detector Training Script for V2-10 Dataset.
Author: Seydi Eryilmaz (@seydivakkas)
Copyright (c) 2026 Seydi Eryilmaz - All Rights Reserved
"""

import os
import sys
import time
import json
import gc
import shutil
import hashlib
import pandas as pd
from pathlib import Path
import torch
from ultralytics import YOLO

ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT_DIR / "artifacts" / "v2-10" / "training.log"
DATASET_YAML = ROOT_DIR / "artifacts" / "v2-10" / "dataset" / "yolo_detect" / "dataset.yaml"
DATASET_MANIFEST = ROOT_DIR / "artifacts" / "v2-10" / "dataset" / "manifest.json"
MODELS_DIR = ROOT_DIR / "artifacts" / "v2-10" / "models"
OUTPUT_DIR = MODELS_DIR / "yolo11n_detect_seed42"
BASE_WEIGHTS = ROOT_DIR / "yolo11n.pt"


class DualLogger:
    """Logs messages to both stdout and a file."""
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log = open(filepath, "a", encoding="utf-8", buffering=1)

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()


def compute_sha256(filepath: Path) -> str:
    if not filepath.exists():
        return "N/A"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536 * 16):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_dataset_fingerprint() -> str:
    if DATASET_MANIFEST.exists():
        with open(DATASET_MANIFEST, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("dataset_sha256_fingerprint") or data.get("dataset_sha256") or "N/A"
    return "N/A"


def train():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Setup dual logging
    logger = DualLogger(LOG_FILE)
    sys.stdout = logger
    sys.stderr = logger

    print("=" * 80)
    print("STARTING YOLO11n V2-10 MOTIF DETECTOR TRAINING")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Root Directory: {ROOT_DIR}")
    print(f"Dataset YAML: {DATASET_YAML}")
    print(f"Base Weights: {BASE_WEIGHTS} (Exists: {BASE_WEIGHTS.exists()})")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
    print("=" * 80)

    # Base weight SHA256
    base_weights_sha = compute_sha256(BASE_WEIGHTS)
    print(f"Base weights SHA256: {base_weights_sha}")
    dataset_fingerprint = get_dataset_fingerprint()
    print(f"Dataset SHA256 Fingerprint: {dataset_fingerprint}")

    hyperparameters = {
        "epochs": 80,
        "patience": 15,
        "imgsz": 640,
        "device": 0,
        "seed": 42,
        "deterministic": True,
        "fliplr": 0.5,
        "flipud": 0.0,  # DIRECTIONAL MOTIF RULE: NEVER FLIP VERTICALLY
        "degrees": 5.0,
        "close_mosaic": 10,
        "cos_lr": True,
        "workers": 4,
        "optimizer": "auto",
        "verbose": True,
        "val": True,
        "plots": True,
        "save": True,
    }

    # Attempt training with batch=32, fallback to batch=16 if OOM
    batch_candidates = [32, 16]
    successful_batch = None
    results = None
    start_time = time.time()

    for batch_size in batch_candidates:
        print(f"\n>>> Attempting training with batch_size = {batch_size} ...")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
        gc.collect()

        try:
            model = YOLO(str(BASE_WEIGHTS))
            train_args = dict(
                data=str(DATASET_YAML),
                project=str(MODELS_DIR),
                name="yolo11n_detect_seed42",
                exist_ok=True,
                batch=batch_size,
                **hyperparameters
            )
            print(f"Ultralytics train arguments: {train_args}")
            results = model.train(**train_args)
            successful_batch = batch_size
            print(f">>> Training completed successfully with batch_size = {batch_size}!")
            break
        except (torch.cuda.OutOfMemoryError, RuntimeError) as e:
            err_msg = str(e).lower()
            if "out of memory" in err_msg or ("cuda" in err_msg and "memory" in err_msg):
                print(f"\n[WARNING] CUDA Out of Memory with batch={batch_size}: {e}")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()
                if batch_size == batch_candidates[-1]:
                    print("[ERROR] Failed even on minimum batch size candidate.")
                    raise
                print("Falling back to next batch size candidate...\n")
            else:
                print(f"[ERROR] Unexpected runtime error: {e}")
                raise
        except Exception as e:
            print(f"[ERROR] Training exception: {e}")
            raise

    duration_seconds = round(time.time() - start_time, 2)
    peak_vram_gb = 0.0
    if torch.cuda.is_available():
        peak_vram_gb = round(torch.cuda.max_memory_allocated(0) / (1024**3), 2)

    print("\n" + "=" * 80)
    print("TRAINING FINISHED")
    print(f"Total Duration: {duration_seconds}s ({duration_seconds/60:.2f} min)")
    print(f"Peak VRAM Allocated: {peak_vram_gb} GB")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 80)

    # Verify output files
    best_pt = OUTPUT_DIR / "weights" / "best.pt"
    last_pt = OUTPUT_DIR / "weights" / "last.pt"
    results_csv = OUTPUT_DIR / "results.csv"

    if not best_pt.exists():
        print(f"[ERROR] best.pt not found at {best_pt}")
    if not last_pt.exists():
        print(f"[ERROR] last.pt not found at {last_pt}")
    if not results_csv.exists():
        print(f"[ERROR] results.csv not found at {results_csv}")

    best_pt_sha = compute_sha256(best_pt)
    last_pt_sha = compute_sha256(last_pt)

    # Parse results.csv for final metrics
    epochs_executed = hyperparameters["epochs"]
    best_epoch = None
    metrics_summary = {}

    if results_csv.exists():
        try:
            df = pd.read_csv(results_csv)
            df.columns = [c.strip() for c in df.columns]
            epochs_executed = len(df)
            print(f"Total Epochs Executed: {epochs_executed}")

            map50_col = next((c for c in df.columns if "mAP50(B)" in c or "mAP_0.5" in c or c == "metrics/mAP50(B)"), None)
            map50_95_col = next((c for c in df.columns if "mAP50-95(B)" in c or "mAP_0.5:0.95" in c or c == "metrics/mAP50-95(B)"), None)
            prec_col = next((c for c in df.columns if "precision(B)" in c or c == "metrics/precision(B)"), None)
            rec_col = next((c for c in df.columns if "recall(B)" in c or c == "metrics/recall(B)"), None)

            if map50_col and map50_col in df:
                best_row_idx = df[map50_col].idxmax()
                best_row = df.iloc[best_row_idx]
                best_epoch = int(best_row["epoch"]) if "epoch" in best_row else int(best_row_idx + 1)
                final_row = df.iloc[-1]

                metrics_summary = {
                    "best_epoch": best_epoch,
                    "best_epoch_metrics": {
                        "mAP50": round(float(best_row[map50_col]), 5),
                        "mAP50-95": round(float(best_row[map50_95_col]), 5) if map50_95_col else None,
                        "precision": round(float(best_row[prec_col]), 5) if prec_col else None,
                        "recall": round(float(best_row[rec_col]), 5) if rec_col else None,
                    },
                    "final_epoch_metrics": {
                        "mAP50": round(float(final_row[map50_col]), 5),
                        "mAP50-95": round(float(final_row[map50_95_col]), 5) if map50_95_col else None,
                        "precision": round(float(final_row[prec_col]), 5) if prec_col else None,
                        "recall": round(float(final_row[rec_col]), 5) if rec_col else None,
                    }
                }
                print("Extracted Metrics Summary:")
                print(json.dumps(metrics_summary, indent=2))
        except Exception as e:
            print(f"[WARNING] Error parsing results.csv: {e}")

    # Build manifest
    manifest_data = {
        "experiment_id": "v2-10-yolo11n-detect-seed42",
        "model_name": "YOLO11n Detect",
        "dataset_version": "v2-10-domain-randomization-v2.0.0",
        "dataset_sha256": dataset_fingerprint,
        "pretrained_checkpoint": "yolo11n.pt",
        "base_weights_sha256": base_weights_sha,
        "best_weights_sha256": best_pt_sha,
        "last_weights_sha256": last_pt_sha,
        "seed": hyperparameters["seed"],
        "imgsz": hyperparameters["imgsz"],
        "batch": successful_batch,
        "epochs_requested": hyperparameters["epochs"],
        "epochs_executed": epochs_executed,
        "best_epoch": best_epoch,
        "duration_seconds": duration_seconds,
        "peak_vram_gb": peak_vram_gb,
        "early_stopping_triggered": epochs_executed < hyperparameters["epochs"],
        "hyperparameters": {
            "patience": hyperparameters["patience"],
            "fliplr": hyperparameters["fliplr"],
            "flipud": hyperparameters["flipud"],
            "degrees": hyperparameters["degrees"],
            "close_mosaic": hyperparameters["close_mosaic"],
            "cos_lr": hyperparameters["cos_lr"],
            "optimizer": hyperparameters["optimizer"],
            "deterministic": hyperparameters["deterministic"],
        },
        "metrics_synthetic_val": metrics_summary.get("best_epoch_metrics", {}),
        "metrics_synthetic_val_final": metrics_summary.get("final_epoch_metrics", {}),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    manifest_file = OUTPUT_DIR / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"\nManifest successfully written to {manifest_file}")
    print("=" * 80)
    print("V2-10 YOLO11n TRAINING RUN COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    train()
