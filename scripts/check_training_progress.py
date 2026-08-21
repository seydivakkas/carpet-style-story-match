import sys
import os
import json
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_CSV = os.path.join(ROOT, "artifacts", "v2-10", "models", "yolo11n_detect_seed42", "results.csv")
LOG_PATH = os.path.join(ROOT, "artifacts", "v2-10", "training.log")

if os.path.exists(RES_CSV):
    try:
        df = pd.read_csv(RES_CSV)
        df.columns = [c.strip() for c in df.columns]
        print(f"Total epochs in results.csv: {len(df)}")
        if len(df) > 0:
            last = df.iloc[-1]
            epoch_num = int(last.get("epoch", len(df)))
            train_box = last.get("train/box_loss", "N/A")
            train_cls = last.get("train/cls_loss", "N/A")
            val_box = last.get("val/box_loss", "N/A")
            val_cls = last.get("val/cls_loss", "N/A")
            map50 = last.get("metrics/mAP50(B)", "N/A")
            map50_95 = last.get("metrics/mAP50-95(B)", "N/A")
            prec = last.get("metrics/precision(B)", "N/A")
            rec = last.get("metrics/recall(B)", "N/A")
            print(f"Epoch {epoch_num:02d}/80 | train_box: {train_box:.4f} | train_cls: {train_cls:.4f} | val_box: {val_box:.4f} | val_cls: {val_cls:.4f} | P: {prec:.4f} | R: {rec:.4f} | mAP50: {map50:.4f} | mAP50-95: {map50_95:.4f}")
    except Exception as e:
        print(f"Error reading results.csv: {e}")
else:
    print("results.csv does not exist yet.")

if os.path.exists(LOG_PATH):
    with open(LOG_PATH, "rb") as f:
        content = f.read().decode("utf-8", errors="ignore")
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    print("\n--- Last 5 lines from training.log ---")
    for l in lines[-5:]:
        print(l)
