import pytest
import uuid

@pytest.mark.asyncio
async def test_create_carpet_success(client):
    payload = {
        "sku": "HERIZ-001",
        "name": "Heriz Traditional Wool Rug",
        "description": "Authentic hand-knotted wool carpet",
        "manufacturer": "Merinos",
        "collection": "Classic Anatolia",
        "width_cm": 200.0,
        "height_cm": 300.0,
        "material": "Wool",
        "style_label": "traditional",
        "source_type": "CATALOG",
        "source_reference": "REF-8921"
    }
    response = await client.post("/api/v1/carpets", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "HERIZ-001"
    assert data["name"] == "Heriz Traditional Wool Rug"
    assert data["width_cm"] == 200.0
    assert data["height_cm"] == 300.0
    assert data["source_type"] == "CATALOG"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

@pytest.mark.asyncio
async def test_create_carpet_empty_sku_normalized_to_none(client):
    payload = {
        "sku": "   ",
        "name": "Minimalist Runner"
    }
    response = await client.post("/api/v1/carpets", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] is None
    assert data["name"] == "Minimalist Runner"

@pytest.mark.asyncio
async def test_create_carpet_invalid_width(client):
    payload = {
        "name": "Invalid Width Carpet",
        "width_cm": 0.0
    }
    response = await client.post("/api/v1/carpets", json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_carpet_invalid_height(client):
    payload = {
        "name": "Invalid Height Carpet",
        "height_cm": -10.5
    }
    response = await client.post("/api/v1/carpets", json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_carpet_blank_name(client):
    payload = {
        "name": "   "
    }
    response = await client.post("/api/v1/carpets", json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_carpet_duplicate_sku_conflict(client):
    payload1 = {
        "sku": "UNIQUE-SKU-123",
        "name": "First Carpet"
    }
    res1 = await client.post("/api/v1/carpets", json=payload1)
    assert res1.status_code == 201

    payload2 = {
        "sku": "UNIQUE-SKU-123",
        "name": "Second Carpet"
    }
    res2 = await client.post("/api/v1/carpets", json=payload2)
    assert res2.status_code == 409
    err = res2.json()
    assert err["detail"]["code"] == "CARPET_SKU_CONFLICT"

@pytest.mark.asyncio
async def test_list_carpets_empty(client):
    response = await client.get("/api/v1/carpets")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 20
    assert data["offset"] == 0

@pytest.mark.asyncio
async def test_list_carpets_pagination_and_filtering(client):
    await client.post("/api/v1/carpets", json={"name": "Carpet 1", "manufacturer": "BrandA", "style_label": "modern"})
    await client.post("/api/v1/carpets", json={"name": "Carpet 2", "manufacturer": "BrandA", "style_label": "traditional"})
    await client.post("/api/v1/carpets", json={"name": "Carpet 3", "manufacturer": "BrandB", "style_label": "modern"})

    res_all = await client.get("/api/v1/carpets")
    assert res_all.status_code == 200
    assert res_all.json()["total"] == 3

    res_filtered = await client.get("/api/v1/carpets?manufacturer=BrandA")
    assert res_filtered.status_code == 200
    assert res_filtered.json()["total"] == 2

    res_limit = await client.get("/api/v1/carpets?limit=1&offset=0")
    assert res_limit.status_code == 200
    assert len(res_limit.json()["items"]) == 1
    assert res_limit.json()["total"] == 3

@pytest.mark.asyncio
async def test_get_carpet_by_id_success(client):
    create_res = await client.post("/api/v1/carpets", json={"name": "Target Carpet"})
    carpet_id = create_res.json()["id"]

    get_res = await client.get(f"/api/v1/carpets/{carpet_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == carpet_id
    assert get_res.json()["name"] == "Target Carpet"

@pytest.mark.asyncio
async def test_get_carpet_by_id_not_found(client):
    random_uuid = str(uuid.uuid4())
    response = await client.get(f"/api/v1/carpets/{random_uuid}")
    assert response.status_code == 404
    err = response.json()
    assert err["detail"]["code"] == "CARPET_NOT_FOUND"

@pytest.mark.asyncio
async def test_patch_carpet_partial_update(client):
    create_res = await client.post("/api/v1/carpets", json={
        "name": "Original Name",
        "manufacturer": "Original Brand",
        "width_cm": 150.0
    })
    carpet_id = create_res.json()["id"]

    patch_payload = {
        "name": "Updated Name",
        "height_cm": 250.0
    }
    patch_res = await client.patch(f"/api/v1/carpets/{carpet_id}", json=patch_payload)
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["name"] == "Updated Name"
    assert updated_data["manufacturer"] == "Original Brand"  # Preserved
    assert updated_data["width_cm"] == 150.0                # Preserved
    assert updated_data["height_cm"] == 250.0               # Newly set

@pytest.mark.asyncio
async def test_delete_carpet_success_and_subsequent_404(client):
    create_res = await client.post("/api/v1/carpets", json={"name": "To Be Deleted"})
    carpet_id = create_res.json()["id"]

    del_res = await client.delete(f"/api/v1/carpets/{carpet_id}")
    assert del_res.status_code == 204

    get_res = await client.get(f"/api/v1/carpets/{carpet_id}")
    assert get_res.status_code == 404
    assert get_res.json()["detail"]["code"] == "CARPET_NOT_FOUND"
