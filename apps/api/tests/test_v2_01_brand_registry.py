"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Unit & Integration Tests for V2-01 Multi-Brand Catalog Architecture.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.manufacturer_brand import ManufacturerBrandModel
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.domain.carpet_catalog.repository import CarpetCatalogRepository
from app.domain.carpet_catalog.brand_registry import BrandParserRegistry
from app.domain.carpet_catalog.merinos_parser import MerinosParser
from app.domain.images.storage import get_image_storage
from app.scripts.seed_brand_registry import seed_brand_registry


@pytest.mark.asyncio
async def test_brand_parser_registry():
    """Verify BrandParserRegistry resolves Merinos parser correctly."""
    registered = BrandParserRegistry.list_registered_brand_keys()
    assert "merinos" in registered

    parser = BrandParserRegistry.get_parser("merinos")
    assert parser is not None
    assert isinstance(parser, MerinosParser)
    assert parser.brand_key == "merinos"
    assert parser.brand_name == "Merinos"
    assert "merinos.com.tr" in parser.base_url


@pytest.mark.asyncio
async def test_manufacturer_brand_model_and_repository(db_session: AsyncSession):
    """Test ManufacturerBrandModel CRUD and CarpetCatalogRepository brand query methods."""
    repo = CarpetCatalogRepository(db_session)

    # 1. Seed brand
    merinos = ManufacturerBrandModel(
        brand_key="merinos",
        brand_name="Merinos",
        brand_website="https://www.merinos.com.tr",
        is_verified=True
    )
    db_session.add(merinos)
    await db_session.flush()

    # 2. List brands
    brands, count = await repo.list_brands()
    assert count >= 1
    merinos_brand = next((b for b in brands if b.brand_key == "merinos"), None)
    assert merinos_brand is not None
    assert merinos_brand.is_verified is True

    # 3. Get brand by key
    fetched = await repo.get_brand_by_key("merinos")
    assert fetched is not None
    assert fetched.id == merinos_brand.id

    # 4. Create secondary test brand
    test_brand = ManufacturerBrandModel(
        brand_key="testbrand",
        brand_name="Test Carpet Brand",
        brand_website="https://www.testcarpet.com",
        is_verified=False
    )
    db_session.add(test_brand)
    await db_session.flush()

    # 5. Create carpet linked to test_brand
    test_carpet = CarpetModel(
        sku="TEST-SKU-V2-01",
        name="Test Brand Carpet",
        source_type=CarpetSourceType.CATALOG,
        brand_id=test_brand.id,
        manufacturer=test_brand.brand_name
    )
    db_session.add(test_carpet)
    await db_session.flush()

    # 6. Filter list_catalog_carpets by brand_key
    carpets, total = await repo.list_catalog_carpets(brand_key="testbrand")
    assert total == 1
    assert carpets[0].sku == "TEST-SKU-V2-01"
    assert carpets[0].brand is not None
    assert carpets[0].brand.brand_key == "testbrand"


@pytest.mark.asyncio
async def test_brands_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    """Test GET /api/v1/brands and GET /api/v1/brands/{brand_key} endpoints."""
    # Seed Merinos brand in session
    merinos = ManufacturerBrandModel(
        brand_key="merinos",
        brand_name="Merinos",
        brand_website="https://www.merinos.com.tr",
        is_verified=True
    )
    db_session.add(merinos)
    await db_session.commit()

    # 1. List brands
    res = await client.get("/api/v1/brands")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    assert any(b["brand_key"] == "merinos" for b in data["brands"])

    # 2. Get brand detail
    res_detail = await client.get("/api/v1/brands/merinos")
    assert res_detail.status_code == 200
    brand_data = res_detail.json()
    assert brand_data["brand_key"] == "merinos"
    assert brand_data["brand_name"] == "Merinos"
    assert brand_data["is_verified"] is True

    # 3. Non-existent brand 404
    res_404 = await client.get("/api/v1/brands/nonexistentbrand")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_catalog_api_brand_key_filter(client: AsyncClient, db_session: AsyncSession):
    """Test GET /api/v1/catalog/carpets?brand_key=merinos."""
    merinos = ManufacturerBrandModel(
        brand_key="merinos",
        brand_name="Merinos",
        brand_website="https://www.merinos.com.tr",
        is_verified=True
    )
    db_session.add(merinos)
    await db_session.flush()

    carpet = CarpetModel(
        sku="TEST-MERINOS-001",
        name="Merinos Elegance Halı",
        source_type=CarpetSourceType.CATALOG,
        brand_id=merinos.id,
        manufacturer="Merinos"
    )
    db_session.add(carpet)
    await db_session.commit()

    res = await client.get("/api/v1/catalog/carpets?brand_key=merinos&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 1
    assert len(data["carpets"]) == 1
    assert data["carpets"][0]["brand"]["brand_key"] == "merinos"


@pytest.mark.asyncio
async def test_image_storage_existence_check():
    """Verify ImageStorage.image_exists method."""
    storage = get_image_storage()
    assert storage.image_exists("carpets/00000000-0000-0000-0000-000000000000/nonexistent.jpg") is False
