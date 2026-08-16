"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Idempotent seed script to initialize Manufacturer Brand Registry with Merinos
and backfill brand_id foreign keys on existing catalog carpets.
"""
import asyncio
import logging
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.db.models.manufacturer_brand import ManufacturerBrandModel
from app.db.models.carpet import CarpetModel, CarpetSourceType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_brand_registry")


async def seed_brand_registry():
    async with AsyncSessionLocal() as session:
        # 1. Seed or get Merinos Brand Record
        stmt = select(ManufacturerBrandModel).where(
            ManufacturerBrandModel.brand_key == "merinos"
        )
        res = await session.execute(stmt)
        merinos_brand = res.scalar_one_or_none()

        if not merinos_brand:
            logger.info("Creating official Merinos manufacturer brand record...")
            merinos_brand = ManufacturerBrandModel(
                brand_key="merinos",
                brand_name="Merinos",
                brand_website="https://www.merinos.com.tr",
                logo_url="https://www.merinos.com.tr/assets/images/logo.png",
                is_verified=True,
                parser_module="app.domain.carpet_catalog.merinos_parser"
            )
            session.add(merinos_brand)
            await session.flush()
            logger.info(f"Created Merinos brand ID: {merinos_brand.id}")
        else:
            logger.info(f"Merinos brand record already exists ID: {merinos_brand.id}")

        # 2. Backfill brand_id on catalog carpets
        backfill_stmt = (
            update(CarpetModel)
            .where(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                CarpetModel.brand_id.is_(None)
            )
            .values(
                brand_id=merinos_brand.id,
                manufacturer="Merinos"
            )
        )
        result = await session.execute(backfill_stmt)
        await session.commit()
        logger.info(f"Backfilled brand_id on {result.rowcount} catalog carpets.")

        # 3. Verify total catalog carpets linked
        count_stmt = select(CarpetModel).where(
            CarpetModel.source_type == CarpetSourceType.CATALOG,
            CarpetModel.brand_id == merinos_brand.id
        )
        count_res = await session.execute(count_stmt)
        total_linked = len(count_res.scalars().all())
        logger.info(f"Total catalog carpets linked to Merinos brand: {total_linked}")


if __name__ == "__main__":
    asyncio.run(seed_brand_registry())
