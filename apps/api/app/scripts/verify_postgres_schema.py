"""Gerçek PostgreSQL Alembic geçişinin minimal bütünlük testi."""
import asyncio
from sqlalchemy import inspect, text
from app.db.session import engine

EXPECTED_TABLES = {
    "upload_analyses", "carpets", "carpet_images", "motif_review_subjects",
    "motif_review_events", "alembic_version",
}
EXPECTED_COLS = {
    "id", "owner_token_sha256", "status", "unified_result", "image_path",
}

async def main() -> None:
    async with engine.connect() as conn:
        tables = set(await conn.run_sync(lambda c: inspect(c).get_table_names()))
        missing = EXPECTED_TABLES - tables
        if missing:
            raise RuntimeError(f"PostgreSQL eksik tablolar: {sorted(missing)}")
        cols = set(await conn.run_sync(
            lambda c: [x["name"] for x in inspect(c).get_columns("upload_analyses")]
        ))
        if EXPECTED_COLS - cols:
            raise RuntimeError(f"upload_analyses eksik alanlar: {sorted(EXPECTED_COLS - cols)}")
        version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
        if version != "2026_10_21_018":
            raise RuntimeError(f"Beklenen Alembic sürümü yok: {version}")
        print("POSTGRESQL_ALEMBIC_SCHEMA_PASS",version)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
