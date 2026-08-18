"""Unit and Integration Test Suite for POST-v1 A6 Real Museum Source Activation."""
import json
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.motif_knowledge import CuratedSourceModel, SourceTypeEnum
from app.db.models.carpet_historical_reference import HistoricalReferenceMetadataModel
from app.db.models.carpet import CarpetModel
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_story_association import (
    CarpetMotifAssociationModel,
    CarpetStoryAssociationModel,
)

from app.domain.museum_sources.adapters.met import MetMuseumSourceAdapter
from app.domain.museum_sources.adapters.vam import VAMuseumSourceAdapter
from app.domain.museum_sources.schemas import (
    AcquisitionStatusEnum,
    A7ReadinessEnum,
)
from app.scripts.activate_museum_sources import run_activation


# --- MOCK FIXTURES ---

RAW_MET_CARPET = {
    "objectID": 446561,
    "accessionNumber": "14.40.714",
    "title": "The Anhalt Medallion Carpet",
    "objectName": "Carpet",
    "classification": "Textiles-Rugs",
    "culture": "Safavid",
    "period": "Safavid period",
    "objectDate": "ca. 1530–50",
    "country": "Iran",
    "medium": "Silk (warp and weft), wool (pile); asymmetrically knotted pile",
    "dimensions": "L. 266 in. (675.6 cm); W. 126 in. (320 cm)",
    "department": "Islamic Art",
    "creditLine": "Gift of Samuel H. Kress Foundation, 1946",
    "isPublicDomain": True,
    "rightsAndReproduction": "CC0 1.0 Universal",
    "primaryImage": "https://images.metmuseum.org/CRDImages/is/original/DP166708.jpg",
    "objectURL": "https://www.metmuseum.org/art/collection/search/446561"
}

RAW_MET_PAINTING = {
    "objectID": 990001,
    "accessionNumber": "PAINTING.001",
    "title": "Portrait of a Merchant sitting on an Oriental Rug",
    "objectName": "Painting",
    "classification": "Paintings",
    "culture": "Dutch",
    "objectDate": "1640",
    "isPublicDomain": True
}

RAW_MET_MISSING_ID = {
    "title": "Unidentified Textile Fragment",
    "objectName": "Carpet",
    "classification": "Textiles-Rugs"
}

RAW_VAM_CARPET = {
    "systemNumber": "O54321",
    "accessionNumber": "272-1893",
    "title": "The Ardabil Carpet",
    "objectType": "Carpet",
    "placesOfOrigin": [{"place": {"text": "Ardabil, Iran"}}],
    "dateText": "1539-1540 (AH 946)",
    "materialsAndTechniques": "Silk warp and weft, wool pile",
    "dimensions": "Height: 1047 cm, Width: 535 cm",
    "department": "Middle Eastern Section",
    "creditLine": "Purchased by public subscription",
    "images": [{"image_id": "2006AM0572_JPG_l", "url": "https://framemark.vam.ac.uk/collections/2006AM0572/full/full/0/default.jpg"}]
}

RAW_VAM_PHOTO = {
    "systemNumber": "O99001",
    "accessionNumber": "E.12-1925",
    "title": "Photograph of Mosque Carpet",
    "objectType": "Photograph",
    "placesOfOrigin": [{"place": {"text": "Istanbul"}}],
    "dateText": "1890"
}


# --- TESTS ---

def test_met_adapter_normalization():
    """Verify Met adapter normalizes valid carpet object into accepted MuseumObjectSourceRecord."""
    adapter = MetMuseumSourceAdapter()
    rec = adapter.normalize_object(RAW_MET_CARPET)

    assert rec.provider_key == "met"
    assert rec.official_object_id == "446561"
    assert rec.source_key == "met-museum-safavid-medallion-carpet-14104"
    assert rec.acquisition_status == AcquisitionStatusEnum.ACCEPTED
    assert rec.a7_readiness == A7ReadinessEnum.READY_FOR_HISTORICAL_CURATION
    assert rec.culture == "Safavid"
    assert rec.rights.open_access is True
    assert rec.rights.public_domain is True
    assert rec.primary_image_source_url == "https://images.metmuseum.org/CRDImages/is/original/DP166708.jpg"

    # Test conversion to SourceImportItem
    src_input = adapter.build_curated_source_input(rec)
    assert src_input.source_key == "met-museum-safavid-medallion-carpet-14104"
    assert src_input.source_type.value == "MUSEUM_OBJECT"
    assert "The Anhalt Medallion Carpet" in src_input.title


def test_vam_adapter_normalization():
    """Verify V&A adapter normalizes valid carpet object into accepted MuseumObjectSourceRecord."""
    adapter = VAMuseumSourceAdapter()
    rec = adapter.normalize_object(RAW_VAM_CARPET)

    assert rec.provider_key == "vam"
    assert rec.official_object_id == "O54321"
    assert rec.source_key == "vam-object-O54321"
    assert rec.acquisition_status == AcquisitionStatusEnum.ACCEPTED
    assert rec.a7_readiness == A7ReadinessEnum.READY_FOR_HISTORICAL_CURATION
    assert rec.culture == "Ardabil, Iran"
    assert rec.rights.rights_statement == "Victoria and Albert Museum, London / Non-Commercial Educational Reuse"
    assert rec.primary_image_source_url == "https://framemark.vam.ac.uk/collections/2006AM0572_JPG_l/full/full/0/default.jpg"


def test_search_false_positive_rejection():
    """Verify non-carpet objects (paintings, photos, books) are rejected as REJECTED_NOT_CARPET."""
    met_adapter = MetMuseumSourceAdapter()
    rec_painting = met_adapter.normalize_object(RAW_MET_PAINTING)
    assert rec_painting.acquisition_status == AcquisitionStatusEnum.REJECTED_NOT_CARPET
    assert rec_painting.a7_readiness == A7ReadinessEnum.NOT_ELIGIBLE
    assert "Painting" in rec_painting.rejection_reason

    vam_adapter = VAMuseumSourceAdapter()
    rec_photo = vam_adapter.normalize_object(RAW_VAM_PHOTO)
    assert rec_photo.acquisition_status == AcquisitionStatusEnum.REJECTED_NOT_CARPET
    assert rec_photo.a7_readiness == A7ReadinessEnum.NOT_ELIGIBLE
    assert "Photograph" in rec_photo.rejection_reason


def test_missing_object_id_rejection():
    """Verify raw payloads missing official object IDs are rejected as INVALID_RECORD."""
    adapter = MetMuseumSourceAdapter()
    rec = adapter.normalize_object(RAW_MET_MISSING_ID)
    assert rec.acquisition_status == AcquisitionStatusEnum.INVALID_RECORD
    assert rec.a7_readiness == A7ReadinessEnum.NOT_ELIGIBLE


def test_unknown_culture_date_preservation():
    """Verify missing culture and date fields are preserved as None without speculative guessing."""
    raw_sparse = {
        "objectID": 777111,
        "title": "Fragmentary Wool Rug",
        "objectName": "Rug",
        "classification": "Textiles-Rugs"
    }
    adapter = MetMuseumSourceAdapter()
    rec = adapter.normalize_object(raw_sparse)

    assert rec.culture is None
    assert rec.period is None
    assert rec.date_display is None
    assert rec.dynasty_or_tradition is None


def test_rights_metadata_separation():
    """Verify metadata rights usability is separated from image reuse permissions."""
    adapter = MetMuseumSourceAdapter()
    rec = adapter.normalize_object(RAW_MET_CARPET)

    # Metadata is usable (ACCEPTED), image is public domain
    assert rec.rights.open_access is True
    assert rec.rights.image_reuse_status == "OPEN_ACCESS_PUBLIC_DOMAIN"

    vam_adapter = VAMuseumSourceAdapter()
    rec_vam = vam_adapter.normalize_object(RAW_VAM_CARPET)
    assert rec_vam.rights.open_access is False
    assert rec_vam.rights.image_reuse_status == "RIGHTS_REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_idempotent_activation_apply(db_session: AsyncSession, monkeypatch):
    """Verify running museum source activation twice in apply mode is idempotent."""
    # Force search_objects to return [] so both runs use identical offline candidates
    monkeypatch.setattr(MetMuseumSourceAdapter, "search_objects", lambda self, query="carpet", limit=20: [])
    monkeypatch.setattr(VAMuseumSourceAdapter, "search_objects", lambda self, query="carpet", limit=20: [])

    res1 = await run_activation(provider_filter="all", limit=10, dry_run=False, apply=True, report=False, db_session=db_session)
    res2 = await run_activation(provider_filter="all", limit=10, dry_run=False, apply=True, report=False, db_session=db_session)

    assert res1["status"] == "PASS"
    assert res2["status"] == "PASS"
    assert res2["database_delta"]["sources_created"] == 0
    assert res2["database_delta"]["sources_unchanged"] > 0


@pytest.mark.asyncio
async def test_db_isolation_and_zero_delta(db_session: AsyncSession, monkeypatch):
    """Verify A6 creates CuratedSource records but 0 HistoricalReference, 0 Carpet, 0 CarpetImage rows."""
    monkeypatch.setattr(MetMuseumSourceAdapter, "search_objects", lambda self, query="carpet", limit=20: [])
    monkeypatch.setattr(VAMuseumSourceAdapter, "search_objects", lambda self, query="carpet", limit=20: [])

    res = await run_activation(provider_filter="all", limit=10, dry_run=False, apply=True, report=False, db_session=db_session)

    assert res["database_delta"]["historical_references_delta"] == 0
    assert res["database_delta"]["historical_carpets_delta"] == 0
    assert res["database_delta"]["carpet_images_delta"] == 0

    # Check database counts delta
    res_hr = await db_session.execute(select(func.count(HistoricalReferenceMetadataModel.id)))
    assert res_hr.scalar_one() == 0
