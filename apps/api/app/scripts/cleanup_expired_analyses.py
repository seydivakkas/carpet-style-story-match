"""Analiz saklama süresi temizlik işi.

Docker Compose içinde ayrı tek işçi olarak sürekli, yerelde --once ile çalışır.
"""
import argparse
import asyncio
import json
from app.db.session import AsyncSessionLocal, dispose_db_engine
from app.domain.images.storage import get_image_storage
from app.domain.result_experience.retention import cleanup_expired_analyses

async def main(once: bool, interval: int, max_records: int) -> None:
    storage = get_image_storage()
    try:
        while True:
            async with AsyncSessionLocal() as db:
                result = await cleanup_expired_analyses(db, storage, max_records=max_records)
            print(json.dumps({"job": "analysis_retention_cleanup", **result}), flush=True)
            if once:
                break
            await asyncio.sleep(interval)
    finally:
        await dispose_db_engine()

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Süresi dolan analizleri ve görüntülerini sil")
    p.add_argument("--once", action="store_true")
    p.add_argument("--interval", type=int, default=3600)
    p.add_argument("--batch-size", type=int, default=100)
    args = p.parse_args()
    if not 60 <= args.interval <= 86400:
        p.error("--interval 60..86400 saniye olmalı")
    if not 1 <= args.batch_size <= 1000:
        p.error("--batch-size 1..1000 olmalı")
    asyncio.run(main(args.once, args.interval, args.batch_size))
