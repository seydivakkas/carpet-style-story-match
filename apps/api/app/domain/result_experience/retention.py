"""Süresi dolan analizleri, görüntüleri ve inceleme bağlantılarını temizler.

Eski kayıtların expires_at alanı NULL'dır: bunlar manuel veri saklama kararı
alınana kadar otomatik olarak silinmez.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.upload_analysis import UploadAnalysisModel
from app.db.models.motif_review import MotifReviewSubjectModel, MotifReviewEventModel
from app.domain.images.storage import ImageStorage

async def cleanup_expired_analyses(
    db: AsyncSession, storage: ImageStorage, *,
    now: Optional[datetime] = None, max_records: int = 100,
) -> dict[str, int]:
    if not 1 <= max_records <= 1000:
        raise ValueError("max_records 1..1000 aralığında olmalı")
    current = now or datetime.now(timezone.utc)
    rows = await db.execute(
        select(UploadAnalysisModel)
        .where(UploadAnalysisModel.expires_at.is_not(None), UploadAnalysisModel.expires_at <= current)
        .order_by(UploadAnalysisModel.expires_at, UploadAnalysisModel.id)
        .limit(max_records)
        .with_for_update(skip_locked=True)
    )
    deleted, failed = 0, 0
    for record in rows.scalars().all():
        try:
            # Önce fiziksel nesne silinir; silme başarısızsa DB kaydı korunur.
            # İşlem tekrar çalıştırıldığında nesne yokluğu idempotent kabul edilir.
            if record.image_path:
                storage.delete_image(record.image_path)
            subrows = await db.execute(
                select(MotifReviewSubjectModel.id)
                .where(MotifReviewSubjectModel.analysis_id == str(record.id))
            )
            ids = list(subrows.scalars().all())
            if ids:
                await db.execute(
                    delete(MotifReviewEventModel)
                    .where(MotifReviewEventModel.review_subject_id.in_(ids))
                )
                await db.execute(
                    delete(MotifReviewSubjectModel)
                    .where(MotifReviewSubjectModel.id.in_(ids))
                )
            await db.delete(record)
            await db.commit()
            deleted += 1
        except Exception:
            await db.rollback()
            failed += 1
    return {"deleted": deleted, "failed": failed}
