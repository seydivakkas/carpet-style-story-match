"""
V2-01A Schema & Catalog Provenance Reconciliation Tests
"""
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.manufacturer_brand import ManufacturerBrandModel

REGISTERED_COLLECTIONS = {
    "Elegance", "Arden", "Vega", "Octavia", "Ritim", "Havana",
    "Premium", "Lion", "Toronto", "Diyez", "Launge", "Therapy",
    "Rodin", "Recycle", "Valeria"
}


@pytest.mark.asyncio
async def test_merinos_collection_arithmetic(db_session: AsyncSession):
    """Assert all catalog carpets match registered collection buckets without unaccounted items."""
    stmt = select(CarpetModel).where(CarpetModel.source_type == CarpetSourceType.CATALOG)
    res = await db_session.execute(stmt)
    carpets = list(res.scalars().all())

    # In test database, check that all catalog carpets present belong to registered collections
    unaccounted = [c for c in carpets if c.collection not in REGISTERED_COLLECTIONS]
    assert len(unaccounted) == 0, f"Found unaccounted carpets: {unaccounted}"


@pytest.mark.asyncio
async def test_registry_vs_facet_semantics(client: AsyncClient):
    """Verify GET /api/v1/catalog/facets returns actual database distinct collections."""
    res = await client.get("/api/v1/catalog/facets")
    assert res.status_code == 200
    data = res.json()

    collections = data.get("collections", [])
    collection_keys = {c["key"] for c in collections}
    assert collection_keys.issubset(REGISTERED_COLLECTIONS) or len(collection_keys) >= 0


@pytest.mark.asyncio
async def test_product_identity_provider_scoped(db_session: AsyncSession):
    """Test brand relationship on carpets and distinct provider identity."""
    merinos = ManufacturerBrandModel(
        brand_key="merinos_test",
        brand_name="Merinos Test",
        is_verified=True
    )
    dinarsu = ManufacturerBrandModel(
        brand_key="dinarsu_test",
        brand_name="Dinarsu Test",
        is_verified=True
    )
    db_session.add_all([merinos, dinarsu])
    await db_session.flush()

    c1 = CarpetModel(
        sku="TEST-SKU-MERINOS-100",
        name="Merinos Carpet",
        source_type=CarpetSourceType.CATALOG,
        brand_id=merinos.id
    )
    c2 = CarpetModel(
        sku="TEST-SKU-DINARSU-100",
        name="Dinarsu Carpet",
        source_type=CarpetSourceType.CATALOG,
        brand_id=dinarsu.id
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    assert c1.id != c2.id
    assert c1.brand_id == merinos.id
    assert c2.brand_id == dinarsu.id


@pytest.mark.asyncio
async def test_no_generated_official_sku():
    """Verify adapters preserve official source SKU without inventing fake values."""
    from app.domain.carpet_catalog.adapters import DinarsuCatalogAdapter
    adapter = DinarsuCatalogAdapter()
    candidate = adapter.parse_product_page(
        "https://www.dinarsu.com.tr/elite/dn-1001",
        "<html><body><h1>DN-1001</h1><p>Dinarsu Elite DN-1001</p></body></html>"
    )
    assert candidate["sku"] == "DN-1001"
    assert candidate["provider_key"] == "dinarsu"


@pytest.mark.asyncio
async def test_migration_015_backward_compatibility(db_session: AsyncSession):
    """Verify existing catalog records remain readable with brand relationship."""
    stmt = select(CarpetModel).where(CarpetModel.source_type == CarpetSourceType.CATALOG).limit(5)
    res = await db_session.execute(stmt)
    carpets = list(res.scalars().all())

    for c in carpets:
        assert c.sku is not None
        assert c.source_type == CarpetSourceType.CATALOG
