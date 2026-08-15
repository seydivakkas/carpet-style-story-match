"""Comprehensive Pytest test suite for Explainable Historical Connection Engine v1."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    CarpetStyleDimensionModel,
    StyleProfileStatus,
    StyleDimensionStatus
)
from app.db.models.motif_knowledge import CuratedSourceModel, SourceTypeEnum
from app.db.models.carpet_historical_reference import (
    HistoricalSourceRoleEnum,
    HistoricalReferenceMetadataModel,
    HistoricalReferenceSourceModel
)
from app.db.models.carpet_historical_connection import (
    HistoricalConnectionStatusEnum,
    HistoricalConnectionLevelEnum
)
from app.domain.historical_connection.constants import HISTORICAL_CONNECTION_VERSION
from app.domain.historical_connection.exceptions import (
    HistoricalConnectionInvalidTargetTypeError,
    HistoricalConnectionTargetProfileFailedError,
    HistoricalConnectionReferenceImageRequiredError,
    HistoricalConnectionReferenceProfileRequiredError,
    HistoricalConnectionReferenceProfileFailedError,
    HistoricalConnectionStyleVersionMismatchError
)
from app.domain.historical_connection.engine import HistoricalConnectionEngine
from app.domain.historical_connection.schemas import HistoricalConnectionCreateInput
from app.domain.historical_connection.service import HistoricalConnectionService


@pytest.fixture
async def sample_sources_and_ref(db_session: AsyncSession):
    """Creates a curated source, historical reference carpet, primary image, and Style DNA profile."""
    museum_src = CuratedSourceModel(
        id=uuid.uuid4(),
        source_key="met-obj-1974.149.34",
        source_type=SourceTypeEnum.MUSEUM_OBJECT,
        title="Metropolitan Museum Object 1974.149.34",
        citation_text="Metropolitan Museum, NYC"
    )
    db_session.add(museum_src)
    await db_session.flush()

    # Historical carpet
    hist_carpet = CarpetModel(
        id=uuid.uuid4(),
        name="Historical Star Ushak",
        source_type=CarpetSourceType.HISTORICAL,
        source_reference="REF-HIST-001",
        is_active=True
    )
    db_session.add(hist_carpet)
    await db_session.flush()

    hist_meta = HistoricalReferenceMetadataModel(
        id=uuid.uuid4(),
        carpet_id=hist_carpet.id,
        reference_key="REF-HIST-001",
        institution_name="The Metropolitan Museum of Art",
        object_identifier="1974.149.34",
        object_title="Star Ushak Carpet",
        culture="Ottoman",
        period="16th Century",
        date_display="ca. 1550"
    )
    db_session.add(hist_meta)

    src_link = HistoricalReferenceSourceModel(
        id=uuid.uuid4(),
        historical_reference_id=hist_meta.id,
        source_id=museum_src.id,
        source_role=HistoricalSourceRoleEnum.PRIMARY_OBJECT_RECORD
    )
    db_session.add(src_link)

    # Reference primary image
    ref_img = CarpetImageModel(
        id=uuid.uuid4(),
        carpet_id=hist_carpet.id,
        original_filename="ref_image.jpg",
        content_type="image/jpeg",
        storage_key="ref/image.jpg",
        byte_size=2048,
        width_px=1000,
        height_px=800,
        channels=3,
        sha256="refhash1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        is_primary=True
    )
    db_session.add(ref_img)
    await db_session.flush()

    # Reference Style DNA Profile (COMPLETE, all 9 dimensions = 0.80)
    ref_profile = CarpetStyleProfileModel(
        id=uuid.uuid4(),
        carpet_id=hist_carpet.id,
        image_id=ref_img.id,
        algorithm_version="style-dna-v1.0.0",
        analysis_input_sha256="refhash1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        analyzed_width_px=1000,
        analyzed_height_px=800,
        status=StyleProfileStatus.COMPLETE
    )
    db_session.add(ref_profile)
    await db_session.flush()

    for key in HistoricalConnectionEngine.CANONICAL_DIMENSIONS:
        dim = CarpetStyleDimensionModel(
            id=uuid.uuid4(),
            profile_id=ref_profile.id,
            dimension_key=key,
            value=0.80,
            confidence=0.90,
            status=StyleDimensionStatus.AVAILABLE
        )
        db_session.add(dim)

    # Catalog Target Carpet
    target_carpet = CarpetModel(
        id=uuid.uuid4(),
        sku="SKU-CATALOG-001",
        name="Catalog Ushak Reproduction",
        source_type=CarpetSourceType.CATALOG,
        is_active=True
    )
    db_session.add(target_carpet)
    await db_session.flush()

    target_img = CarpetImageModel(
        id=uuid.uuid4(),
        carpet_id=target_carpet.id,
        original_filename="target_image.jpg",
        content_type="image/jpeg",
        storage_key="target/image.jpg",
        byte_size=2048,
        width_px=1000,
        height_px=800,
        channels=3,
        sha256="targethash1234567890abcdef1234567890abcdef1234567890abcdef123456",
        is_primary=True
    )
    db_session.add(target_img)
    await db_session.flush()

    target_profile = CarpetStyleProfileModel(
        id=uuid.uuid4(),
        carpet_id=target_carpet.id,
        image_id=target_img.id,
        algorithm_version="style-dna-v1.0.0",
        analysis_input_sha256="targethash1234567890abcdef1234567890abcdef1234567890abcdef123456",
        analyzed_width_px=1000,
        analyzed_height_px=800,
        status=StyleProfileStatus.COMPLETE
    )
    db_session.add(target_profile)
    await db_session.flush()

    for key in HistoricalConnectionEngine.CANONICAL_DIMENSIONS:
        dim = CarpetStyleDimensionModel(
            id=uuid.uuid4(),
            profile_id=target_profile.id,
            dimension_key=key,
            value=0.80,
            confidence=0.95,
            status=StyleDimensionStatus.AVAILABLE
        )
        db_session.add(dim)

    await db_session.commit()

    return {
        "museum_source": museum_src,
        "hist_carpet": hist_carpet,
        "hist_meta": hist_meta,
        "ref_profile": ref_profile,
        "target_carpet": target_carpet,
        "target_profile": target_profile
    }


@pytest.mark.asyncio
async def test_identical_style_dna(db_session: AsyncSession, sample_sources_and_ref):
    """Tests identical Style DNA produces similarity 1.0 and VERY_CLOSE connection level."""
    service = HistoricalConnectionService(db_session)
    res = await service.create_historical_connection(
        HistoricalConnectionCreateInput(
            target_style_profile_id=sample_sources_and_ref["target_profile"].id,
            historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
        )
    )

    assert res.status == HistoricalConnectionStatusEnum.COMPLETE
    assert res.style_similarity == 1.0
    assert res.connection_level == HistoricalConnectionLevelEnum.VERY_CLOSE
    assert res.comparable_dimension_count == 9
    assert res.dimension_coverage == 1.0
    assert res.explanation.connection_level_label_tr == "Çok Yakın Görsel Tarihsel Bağlantı"


@pytest.mark.asyncio
async def test_opposite_style_dna(db_session: AsyncSession, sample_sources_and_ref):
    """Tests target=0.0 and ref=1.0 produces similarity 0.0 and LIMITED level."""
    # Update target dimensions to 0.0
    target_prof = sample_sources_and_ref["target_profile"]
    stmt = select(CarpetStyleDimensionModel).where(CarpetStyleDimensionModel.profile_id == target_prof.id)
    res_dims = await db_session.execute(stmt)
    for dim in res_dims.scalars().all():
        dim.value = 0.0

    ref_prof = sample_sources_and_ref["ref_profile"]
    stmt2 = select(CarpetStyleDimensionModel).where(CarpetStyleDimensionModel.profile_id == ref_prof.id)
    res_dims2 = await db_session.execute(stmt2)
    for dim in res_dims2.scalars().all():
        dim.value = 1.0

    await db_session.commit()

    service = HistoricalConnectionService(db_session)
    res = await service.create_historical_connection(
        HistoricalConnectionCreateInput(
            target_style_profile_id=target_prof.id,
            historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
        )
    )

    assert res.status == HistoricalConnectionStatusEnum.COMPLETE
    assert res.style_similarity == 0.0
    assert res.connection_level == HistoricalConnectionLevelEnum.LIMITED


@pytest.mark.asyncio
async def test_midpoint_difference(db_session: AsyncSession, sample_sources_and_ref):
    """Tests target=0.20 and ref=0.70 produces diff=0.50, similarity=0.50."""
    target_prof = sample_sources_and_ref["target_profile"]
    stmt = select(CarpetStyleDimensionModel).where(CarpetStyleDimensionModel.profile_id == target_prof.id)
    res_dims = await db_session.execute(stmt)
    for dim in res_dims.scalars().all():
        dim.value = 0.20

    ref_prof = sample_sources_and_ref["ref_profile"]
    stmt2 = select(CarpetStyleDimensionModel).where(CarpetStyleDimensionModel.profile_id == ref_prof.id)
    res_dims2 = await db_session.execute(stmt2)
    for dim in res_dims2.scalars().all():
        dim.value = 0.70

    await db_session.commit()

    service = HistoricalConnectionService(db_session)
    res = await service.create_historical_connection(
        HistoricalConnectionCreateInput(
            target_style_profile_id=target_prof.id,
            historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
        )
    )

    assert res.style_similarity == 0.50
    assert res.connection_level == HistoricalConnectionLevelEnum.LIMITED
    assert res.dimensions[0].difference == 0.50
    assert res.dimensions[0].similarity == 0.50


@pytest.mark.asyncio
async def test_confidence_invariance(db_session: AsyncSession, sample_sources_and_ref):
    """Tests changing confidence score does not alter similarity calculation."""
    target_prof = sample_sources_and_ref["target_profile"]
    stmt = select(CarpetStyleDimensionModel).where(CarpetStyleDimensionModel.profile_id == target_prof.id)
    res_dims = await db_session.execute(stmt)
    for dim in res_dims.scalars().all():
        dim.value = 0.50
        dim.confidence = 0.10  # Low confidence

    ref_prof = sample_sources_and_ref["ref_profile"]
    stmt2 = select(CarpetStyleDimensionModel).where(CarpetStyleDimensionModel.profile_id == ref_prof.id)
    res_dims2 = await db_session.execute(stmt2)
    for dim in res_dims2.scalars().all():
        dim.value = 0.80
        dim.confidence = 0.99  # High confidence

    await db_session.commit()

    service = HistoricalConnectionService(db_session)
    res = await service.create_historical_connection(
        HistoricalConnectionCreateInput(
            target_style_profile_id=target_prof.id,
            historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
        )
    )

    # difference = 0.30, similarity = 0.70 (independent of confidence scores)
    assert res.style_similarity == 0.70
    assert res.connection_level == HistoricalConnectionLevelEnum.MODERATE


@pytest.mark.asyncio
async def test_low_confidence_comparable(db_session: AsyncSession, sample_sources_and_ref):
    """Tests LOW_CONFIDENCE dimension status remains comparable and is recorded in explanation."""
    target_prof = sample_sources_and_ref["target_profile"]
    stmt = select(CarpetStyleDimensionModel).where(
        CarpetStyleDimensionModel.profile_id == target_prof.id,
        CarpetStyleDimensionModel.dimension_key == "color_energy"
    )
    res = await db_session.execute(stmt)
    dim = res.scalar_one()
    dim.status = StyleDimensionStatus.LOW_CONFIDENCE

    await db_session.commit()

    service = HistoricalConnectionService(db_session)
    res_conn = await service.create_historical_connection(
        HistoricalConnectionCreateInput(
            target_style_profile_id=target_prof.id,
            historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
        )
    )

    assert res_conn.comparable_dimension_count == 9
    assert "color_energy" in res_conn.explanation.low_confidence_dimensions


@pytest.mark.asyncio
async def test_partial_coverage(db_session: AsyncSession, sample_sources_and_ref):
    """Tests 8 comparable dimensions produces status PARTIAL and coverage_note."""
    target_prof = sample_sources_and_ref["target_profile"]
    stmt = select(CarpetStyleDimensionModel).where(
        CarpetStyleDimensionModel.profile_id == target_prof.id,
        CarpetStyleDimensionModel.dimension_key == "color_energy"
    )
    res = await db_session.execute(stmt)
    dim = res.scalar_one()
    dim.status = StyleDimensionStatus.NOT_AVAILABLE

    await db_session.commit()

    service = HistoricalConnectionService(db_session)
    res_conn = await service.create_historical_connection(
        HistoricalConnectionCreateInput(
            target_style_profile_id=target_prof.id,
            historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
        )
    )

    assert res_conn.status == HistoricalConnectionStatusEnum.PARTIAL
    assert res_conn.comparable_dimension_count == 8
    assert res_conn.dimension_coverage == 0.8889
    assert res_conn.style_similarity is not None
    assert res_conn.explanation.coverage_note is not None


@pytest.mark.asyncio
async def test_insufficient_coverage_five_dimensions(db_session: AsyncSession, sample_sources_and_ref):
    """Tests 5 comparable dimensions produces NOT_AVAILABLE status and null similarity."""
    target_prof = sample_sources_and_ref["target_profile"]
    stmt = select(CarpetStyleDimensionModel).where(CarpetStyleDimensionModel.profile_id == target_prof.id)
    res = await db_session.execute(stmt)
    dims = res.scalars().all()
    # Set 4 dimensions to NOT_AVAILABLE (leaves 5 comparable)
    for dim in dims[:4]:
        dim.status = StyleDimensionStatus.NOT_AVAILABLE

    await db_session.commit()

    service = HistoricalConnectionService(db_session)
    res_conn = await service.create_historical_connection(
        HistoricalConnectionCreateInput(
            target_style_profile_id=target_prof.id,
            historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
        )
    )

    assert res_conn.status == HistoricalConnectionStatusEnum.NOT_AVAILABLE
    assert res_conn.not_available_reason == "INSUFFICIENT_COMPARABLE_DIMENSIONS"
    assert res_conn.style_similarity is None
    assert res_conn.connection_level is None
    assert res_conn.comparable_dimension_count == 5


@pytest.mark.asyncio
async def test_metadata_invariance(db_session: AsyncSession, sample_sources_and_ref):
    """Tests changing historical reference metadata (culture, period) does NOT alter similarity score."""
    hist_meta = sample_sources_and_ref["hist_meta"]
    target_prof = sample_sources_and_ref["target_profile"]

    service = HistoricalConnectionService(db_session)
    res1 = await service.create_historical_connection(
        HistoricalConnectionCreateInput(
            target_style_profile_id=target_prof.id,
            historical_reference_id=hist_meta.reference_key
        )
    )
    score1 = res1.style_similarity

    # Alter metadata fields
    hist_meta.culture = "Altered Persian"
    hist_meta.period = "19th Century"
    await db_session.commit()

    res2 = await service.get_historical_connection_detail(res1.id)
    score2 = res2.style_similarity

    assert score1 == score2
    assert res2.explanation.reference_context.culture == "Altered Persian"


@pytest.mark.asyncio
async def test_target_type_rejection(db_session: AsyncSession, sample_sources_and_ref):
    """Tests rejecting a target profile that belongs to a HISTORICAL carpet."""
    ref_prof = sample_sources_and_ref["ref_profile"]
    hist_meta = sample_sources_and_ref["hist_meta"]

    service = HistoricalConnectionService(db_session)
    with pytest.raises(HistoricalConnectionInvalidTargetTypeError):
        await service.create_historical_connection(
            HistoricalConnectionCreateInput(
                target_style_profile_id=ref_prof.id,  # Target is HISTORICAL carpet
                historical_reference_id=hist_meta.reference_key
            )
        )


@pytest.mark.asyncio
async def test_no_local_reference_image(db_session: AsyncSession, sample_sources_and_ref):
    """Tests historical reference missing a local primary CarpetImage raises exception."""
    # Create historical reference without image
    hist_carpet2 = CarpetModel(
        id=uuid.uuid4(),
        name="No Image Reference",
        source_type=CarpetSourceType.HISTORICAL,
        source_reference="REF-NO-IMAGE",
        is_active=True
    )
    db_session.add(hist_carpet2)
    hist_meta2 = HistoricalReferenceMetadataModel(
        id=uuid.uuid4(),
        carpet_id=hist_carpet2.id,
        reference_key="REF-NO-IMAGE",
        institution_name="Test Museum",
        object_identifier="OBJ-999",
        object_title="No Image Carpet",
        source_image_url="https://example.com/external.jpg"  # Metadata URL only!
    )
    db_session.add(hist_meta2)
    await db_session.commit()

    service = HistoricalConnectionService(db_session)
    with pytest.raises(HistoricalConnectionReferenceImageRequiredError):
        await service.create_historical_connection(
            HistoricalConnectionCreateInput(
                target_style_profile_id=sample_sources_and_ref["target_profile"].id,
                historical_reference_id="REF-NO-IMAGE"
            )
        )


@pytest.mark.asyncio
async def test_reference_profile_failed(db_session: AsyncSession, sample_sources_and_ref):
    """Tests reference profile with FAILED status raises exception."""
    ref_prof = sample_sources_and_ref["ref_profile"]
    ref_prof.status = StyleProfileStatus.FAILED
    await db_session.commit()

    service = HistoricalConnectionService(db_session)
    with pytest.raises(HistoricalConnectionReferenceProfileFailedError):
        await service.create_historical_connection(
            HistoricalConnectionCreateInput(
                target_style_profile_id=sample_sources_and_ref["target_profile"].id,
                historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
            )
        )


@pytest.mark.asyncio
async def test_version_mismatch(db_session: AsyncSession, sample_sources_and_ref):
    """Tests algorithm version mismatch raises exception."""
    target_prof = sample_sources_and_ref["target_profile"]
    target_prof.algorithm_version = "style-dna-v2.0.0"
    await db_session.commit()

    service = HistoricalConnectionService(db_session)
    with pytest.raises(HistoricalConnectionStyleVersionMismatchError):
        await service.create_historical_connection(
            HistoricalConnectionCreateInput(
                target_style_profile_id=target_prof.id,
                historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
            )
        )


@pytest.mark.asyncio
async def test_exactly_9_snapshots(db_session: AsyncSession, sample_sources_and_ref):
    """Tests persisted connection result contains exactly 9 dimension rows in canonical order."""
    service = HistoricalConnectionService(db_session)
    res = await service.create_historical_connection(
        HistoricalConnectionCreateInput(
            target_style_profile_id=sample_sources_and_ref["target_profile"].id,
            historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
        )
    )

    assert len(res.dimensions) == 9
    dim_keys = [d.dimension_key for d in res.dimensions]
    assert dim_keys == HistoricalConnectionEngine.CANONICAL_DIMENSIONS


@pytest.mark.asyncio
async def test_idempotency(db_session: AsyncSession, sample_sources_and_ref):
    """Tests creating connection twice for same target & reference profile returns identical result ID."""
    service = HistoricalConnectionService(db_session)
    input_data = HistoricalConnectionCreateInput(
        target_style_profile_id=sample_sources_and_ref["target_profile"].id,
        historical_reference_id=sample_sources_and_ref["hist_meta"].reference_key
    )

    res1 = await service.create_historical_connection(input_data)
    res2 = await service.create_historical_connection(input_data)

    assert res1.id == res2.id


@pytest.mark.asyncio
async def test_threshold_level_boundaries(db_session: AsyncSession, sample_sources_and_ref):
    """Tests boundary thresholds for VERY_CLOSE (>=0.90), CLOSE (>=0.75), MODERATE (>=0.60), LIMITED (<0.60)."""
    target_prof = sample_sources_and_ref["target_profile"]
    ref_prof = sample_sources_and_ref["ref_profile"]
    service = HistoricalConnectionService(db_session)

    # 1. VERY_CLOSE (sim = 0.90)
    stmt = select(CarpetStyleDimensionModel).where(CarpetStyleDimensionModel.profile_id == target_prof.id)
    res_dims = await db_session.execute(stmt)
    for dim in res_dims.scalars().all():
        dim.value = 0.90
    stmt2 = select(CarpetStyleDimensionModel).where(CarpetStyleDimensionModel.profile_id == ref_prof.id)
    res_dims2 = await db_session.execute(stmt2)
    for dim in res_dims2.scalars().all():
        dim.value = 1.00
    await db_session.commit()

    # Clear previous connection for new evaluation fixture
    res_vc = HistoricalConnectionEngine.evaluate(
        target_dimensions=(await db_session.execute(stmt)).scalars().all(),
        reference_dimensions=(await db_session.execute(stmt2)).scalars().all()
    )
    assert res_vc["style_similarity"] == 0.90
    assert res_vc["connection_level"] == HistoricalConnectionLevelEnum.VERY_CLOSE

    # 2. CLOSE (sim = 0.8999 -> 0.75)
    for dim in (await db_session.execute(stmt)).scalars().all():
        dim.value = 0.8999
    await db_session.commit()

    res_close = HistoricalConnectionEngine.evaluate(
        target_dimensions=(await db_session.execute(stmt)).scalars().all(),
        reference_dimensions=(await db_session.execute(stmt2)).scalars().all()
    )
    assert res_close["style_similarity"] == 0.8999
    assert res_close["connection_level"] == HistoricalConnectionLevelEnum.CLOSE

    # 3. MODERATE (sim = 0.60)
    for dim in (await db_session.execute(stmt)).scalars().all():
        dim.value = 0.60
    await db_session.commit()

    res_mod = HistoricalConnectionEngine.evaluate(
        target_dimensions=(await db_session.execute(stmt)).scalars().all(),
        reference_dimensions=(await db_session.execute(stmt2)).scalars().all()
    )
    assert res_mod["style_similarity"] == 0.60
    assert res_mod["connection_level"] == HistoricalConnectionLevelEnum.MODERATE

    # 4. LIMITED (sim = 0.5999)
    for dim in (await db_session.execute(stmt)).scalars().all():
        dim.value = 0.5999
    await db_session.commit()

    res_lim = HistoricalConnectionEngine.evaluate(
        target_dimensions=(await db_session.execute(stmt)).scalars().all(),
        reference_dimensions=(await db_session.execute(stmt2)).scalars().all()
    )
    assert res_lim["style_similarity"] == 0.5999
    assert res_lim["connection_level"] == HistoricalConnectionLevelEnum.LIMITED


@pytest.mark.asyncio
async def test_api_create_get_list_meta(client: AsyncClient, db_session: AsyncSession, sample_sources_and_ref):
    """End-to-end API testing for POST, GET detail, GET list, and GET meta endpoints."""
    target_prof_id = str(sample_sources_and_ref["target_profile"].id)
    ref_key = sample_sources_and_ref["hist_meta"].reference_key

    # 1. POST /api/v1/historical-connections
    resp = await client.post(
        "/api/v1/historical-connections",
        json={
            "target_style_profile_id": target_prof_id,
            "historical_reference_id": ref_key
        }
    )
    assert resp.status_code == 201
    data = resp.json()

    conn_id = data["id"]
    assert data["connection_version"] == HISTORICAL_CONNECTION_VERSION
    assert data["status"] == "COMPLETE"
    assert data["style_similarity"] == 1.0
    assert data["explanation"]["disclaimer"] is not None
    assert data["explanation"]["reference_context"]["institution_name"] == "The Metropolitan Museum of Art"

    # 2. GET /api/v1/historical-connections/{conn_id}
    resp_get = await client.get(f"/api/v1/historical-connections/{conn_id}")
    assert resp_get.status_code == 200
    detail = resp_get.json()
    assert detail["id"] == conn_id

    # 3. GET /api/v1/historical-connections (list)
    resp_list = await client.get(f"/api/v1/historical-connections?target_style_profile_id={target_prof_id}")
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["total_count"] == 1

    # 4. GET /api/v1/meta/historical-connections
    resp_meta = await client.get("/api/v1/meta/historical-connections")
    assert resp_meta.status_code == 200
    meta_data = resp_meta.json()
    assert meta_data["connection_version"] == HISTORICAL_CONNECTION_VERSION
    assert "VERY_CLOSE" in meta_data["connection_levels"]
