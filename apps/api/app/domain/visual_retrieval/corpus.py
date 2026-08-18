"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Corpus Providers and Eligibility Filter v1.0.0
"""
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_image import CarpetImageModel
from app.db.models.carpet_historical_reference import HistoricalReferenceMetadataModel
from app.db.models.carpet_style_profile import (
    CarpetStyleProfileModel,
    StyleProfileStatus,
    StyleDimensionStatus,
)
from app.domain.visual_retrieval.models import (
    CANONICAL_STYLE_DNA_VERSION,
    CANONICAL_DIMENSION_KEYS,
    CatalogCorpusAccounting,
    HistoricalCorpusAccounting,
)


class CatalogCandidateRecord:
    def __init__(
        self,
        catalog_id: str,
        sku: str,
        brand: str,
        collection: Optional[str],
        product_name: str,
        primary_image_url: Optional[str],
        vector: Dict[str, float],
        source_metadata_provenance: Dict[str, Any],
    ):
        self.catalog_id = catalog_id
        self.sku = sku
        self.brand = brand
        self.collection = collection
        self.product_name = product_name
        self.primary_image_url = primary_image_url
        self.vector = vector
        self.source_metadata_provenance = source_metadata_provenance


class HistoricalCandidateRecord:
    def __init__(
        self,
        historical_reference_id: str,
        reference_key: str,
        institution: str,
        object_title: str,
        museum_object_id: Optional[str],
        canonical_source_url: Optional[str],
        primary_image_url: Optional[str],
        museum_metadata: Dict[str, Any],
        vector: Dict[str, float],
        metadata_provenance: Dict[str, Any],
    ):
        self.historical_reference_id = historical_reference_id
        self.reference_key = reference_key
        self.institution = institution
        self.object_title = object_title
        self.museum_object_id = museum_object_id
        self.canonical_source_url = canonical_source_url
        self.primary_image_url = primary_image_url
        self.museum_metadata = museum_metadata
        self.vector = vector
        self.metadata_provenance = metadata_provenance


def compute_corpus_fingerprint(records: List[Tuple[str, Dict[str, float]]]) -> str:
    """
    Computes a deterministic SHA-256 fingerprint for a list of (id, 9d_vector) tuples.
    Items are sorted by ID to ensure hash stability across database query order changes.
    """
    sorted_records = sorted(records, key=lambda r: r[0])
    hasher = hashlib.sha256()
    hasher.update(CANONICAL_STYLE_DNA_VERSION.encode("utf-8"))

    for rec_id, vec in sorted_records:
        vec_tuple = tuple(round(float(vec[k]), 4) for k in CANONICAL_DIMENSION_KEYS)
        entry_str = f"{rec_id}:{vec_tuple}"
        hasher.update(entry_str.encode("utf-8"))

    return hasher.hexdigest()


class CatalogVisualCorpusProvider:
    """Loads and validates eligible catalog products with COMPLETE Style DNA."""

    @staticmethod
    async def load_eligible_corpus_async(
        db: AsyncSession,
    ) -> Tuple[List[CatalogCandidateRecord], CatalogCorpusAccounting]:
        # Query total catalog products with eager loading of brand
        stmt_tot = (
            select(CarpetModel)
            .options(selectinload(CarpetModel.brand))
            .where(CarpetModel.source_type == CarpetSourceType.CATALOG)
        )
        res_tot = await db.execute(stmt_tot)
        all_carpets = list(res_tot.scalars().all())
        total_records = len(all_carpets)

        # Query primary images
        stmt_img = (
            select(CarpetImageModel)
            .join(CarpetModel)
            .where(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                CarpetImageModel.is_primary.is_(True),
            )
        )
        res_img = await db.execute(stmt_img)
        primary_images = {img.carpet_id: img for img in res_img.scalars().all()}

        # Query Style Profiles
        stmt_prof = (
            select(CarpetStyleProfileModel)
            .options(selectinload(CarpetStyleProfileModel.dimensions))
            .join(CarpetModel)
            .where(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                CarpetStyleProfileModel.algorithm_version == CANONICAL_STYLE_DNA_VERSION,
            )
        )
        res_prof = await db.execute(stmt_prof)
        profiles = {prof.carpet_id: prof for prof in res_prof.scalars().all()}

        eligible_candidates: List[CatalogCandidateRecord] = []
        fp_entries: List[Tuple[str, Dict[str, float]]] = []

        excluded_partial = 0
        excluded_missing_primary_image = 0
        excluded_missing_style_dna = 0

        for carpet in all_carpets:
            c_id = str(carpet.id)
            sku = carpet.sku

            # Exclude test fixtures or non-catalog specimens if any
            if sku and sku.startswith("DN-"):
                continue

            p_img = primary_images.get(carpet.id)
            p_prof = profiles.get(carpet.id)

            if not p_img:
                excluded_missing_primary_image += 1
                continue

            if not p_prof:
                excluded_missing_style_dna += 1
                continue

            if p_prof.status == StyleProfileStatus.PARTIAL:
                excluded_partial += 1
                continue

            if p_prof.status != StyleProfileStatus.COMPLETE:
                continue

            # Extract 9D vector
            dim_map = {d.dimension_key: d.value for d in p_prof.dimensions if d.status in [StyleDimensionStatus.AVAILABLE, StyleDimensionStatus.LOW_CONFIDENCE] and d.value is not None}
            if len(dim_map) != 9 or not set(CANONICAL_DIMENSION_KEYS).issubset(set(dim_map.keys())):
                excluded_partial += 1
                continue

            vector = {k: float(dim_map[k]) for k in CANONICAL_DIMENSION_KEYS}
            img_url = f"/api/v1/carpets/{c_id}/primary-image" if p_img else None
            brand_name = carpet.brand.brand_name if carpet.brand else (carpet.manufacturer or "Merinos")

            candidate = CatalogCandidateRecord(
                catalog_id=c_id,
                sku=carpet.sku or f"SKU-{c_id[:8]}",
                brand=brand_name,
                collection=carpet.collection,
                product_name=carpet.name or f"{brand_name} {carpet.collection or ''} {carpet.sku or ''}".strip(),
                primary_image_url=img_url,
                vector=vector,
                source_metadata_provenance={
                    "source_type": "CATALOG",
                    "sku": carpet.sku,
                    "brand": brand_name,
                    "metadata_assertion": "OFFICIAL_CATALOG_METADATA",
                },
            )
            eligible_candidates.append(candidate)
            fp_entries.append((c_id, vector))

        fingerprint = compute_corpus_fingerprint(fp_entries)

        accounting = CatalogCorpusAccounting(
            total_records=total_records,
            eligible_records=len(eligible_candidates),
            excluded_partial=excluded_partial,
            excluded_missing_primary_image=excluded_missing_primary_image,
            excluded_missing_style_dna=excluded_missing_style_dna,
            corpus_fingerprint=fingerprint,
        )

        return eligible_candidates, accounting

    @staticmethod
    def load_eligible_corpus_sync(
        db: Session,
    ) -> Tuple[List[CatalogCandidateRecord], CatalogCorpusAccounting]:
        all_carpets = (
            db.query(CarpetModel)
            .options(selectinload(CarpetModel.brand))
            .filter(CarpetModel.source_type == CarpetSourceType.CATALOG)
            .all()
        )
        total_records = len(all_carpets)

        primary_images_list = (
            db.query(CarpetImageModel)
            .join(CarpetModel)
            .filter(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                CarpetImageModel.is_primary.is_(True),
            )
            .all()
        )
        primary_images = {img.carpet_id: img for img in primary_images_list}

        profiles_list = (
            db.query(CarpetStyleProfileModel)
            .options(selectinload(CarpetStyleProfileModel.dimensions))
            .join(CarpetModel)
            .filter(
                CarpetModel.source_type == CarpetSourceType.CATALOG,
                CarpetStyleProfileModel.algorithm_version == CANONICAL_STYLE_DNA_VERSION,
            )
            .all()
        )
        profiles = {prof.carpet_id: prof for prof in profiles_list}

        eligible_candidates: List[CatalogCandidateRecord] = []
        fp_entries: List[Tuple[str, Dict[str, float]]] = []

        excluded_partial = 0
        excluded_missing_primary_image = 0
        excluded_missing_style_dna = 0

        for carpet in all_carpets:
            c_id = str(carpet.id)
            sku = carpet.sku

            if sku and sku.startswith("DN-"):
                continue

            p_img = primary_images.get(carpet.id)
            p_prof = profiles.get(carpet.id)

            if not p_img:
                excluded_missing_primary_image += 1
                continue

            if not p_prof:
                excluded_missing_style_dna += 1
                continue

            if p_prof.status == StyleProfileStatus.PARTIAL:
                excluded_partial += 1
                continue

            if p_prof.status != StyleProfileStatus.COMPLETE:
                continue

            dim_map = {d.dimension_key: d.value for d in p_prof.dimensions if d.status in [StyleDimensionStatus.AVAILABLE, StyleDimensionStatus.LOW_CONFIDENCE] and d.value is not None}
            if len(dim_map) != 9 or not set(CANONICAL_DIMENSION_KEYS).issubset(set(dim_map.keys())):
                excluded_partial += 1
                continue

            vector = {k: float(dim_map[k]) for k in CANONICAL_DIMENSION_KEYS}
            img_url = f"/api/v1/carpets/{c_id}/primary-image" if p_img else None
            brand_name = carpet.brand.brand_name if carpet.brand else (carpet.manufacturer or "Merinos")

            candidate = CatalogCandidateRecord(
                catalog_id=c_id,
                sku=carpet.sku or f"SKU-{c_id[:8]}",
                brand=brand_name,
                collection=carpet.collection,
                product_name=carpet.name or f"{brand_name} {carpet.collection or ''} {carpet.sku or ''}".strip(),
                primary_image_url=img_url,
                vector=vector,
                source_metadata_provenance={
                    "source_type": "CATALOG",
                    "sku": carpet.sku,
                    "brand": brand_name,
                    "metadata_assertion": "OFFICIAL_CATALOG_METADATA",
                },
            )
            eligible_candidates.append(candidate)
            fp_entries.append((c_id, vector))

        fingerprint = compute_corpus_fingerprint(fp_entries)

        accounting = CatalogCorpusAccounting(
            total_records=total_records,
            eligible_records=len(eligible_candidates),
            excluded_partial=excluded_partial,
            excluded_missing_primary_image=excluded_missing_primary_image,
            excluded_missing_style_dna=excluded_missing_style_dna,
            corpus_fingerprint=fingerprint,
        )

        return eligible_candidates, accounting


class HistoricalVisualCorpusProvider:
    """Loads and validates eligible historical references with primary image and COMPLETE Style DNA."""

    @staticmethod
    async def load_eligible_corpus_async(
        db: AsyncSession,
    ) -> Tuple[List[HistoricalCandidateRecord], HistoricalCorpusAccounting]:
        stmt_tot = select(HistoricalReferenceMetadataModel).options(
            selectinload(HistoricalReferenceMetadataModel.carpet)
        )
        res_tot = await db.execute(stmt_tot)
        all_hist = list(res_tot.scalars().all())
        total_records = len(all_hist)

        stmt_img = (
            select(CarpetImageModel)
            .join(CarpetModel)
            .where(
                CarpetModel.source_type == CarpetSourceType.HISTORICAL,
                CarpetImageModel.is_primary.is_(True),
            )
        )
        res_img = await db.execute(stmt_img)
        primary_images = {img.carpet_id: img for img in res_img.scalars().all()}

        stmt_prof = (
            select(CarpetStyleProfileModel)
            .options(selectinload(CarpetStyleProfileModel.dimensions))
            .join(CarpetModel)
            .where(
                CarpetModel.source_type == CarpetSourceType.HISTORICAL,
                CarpetStyleProfileModel.algorithm_version == CANONICAL_STYLE_DNA_VERSION,
            )
        )
        res_prof = await db.execute(stmt_prof)
        profiles = {prof.carpet_id: prof for prof in res_prof.scalars().all()}

        eligible_candidates: List[HistoricalCandidateRecord] = []
        fp_entries: List[Tuple[str, Dict[str, float]]] = []

        excluded_missing_primary_image = 0
        excluded_missing_style_dna = 0

        for meta in all_hist:
            h_id = str(meta.id)
            carpet_id = meta.carpet_id

            p_img = primary_images.get(carpet_id)
            p_prof = profiles.get(carpet_id)

            if not p_img:
                excluded_missing_primary_image += 1
                continue

            if not p_prof:
                excluded_missing_style_dna += 1
                continue

            if p_prof.status != StyleProfileStatus.COMPLETE:
                excluded_missing_style_dna += 1
                continue

            dim_map = {d.dimension_key: d.value for d in p_prof.dimensions if d.status in [StyleDimensionStatus.AVAILABLE, StyleDimensionStatus.LOW_CONFIDENCE] and d.value is not None}
            if len(dim_map) != 9 or not set(CANONICAL_DIMENSION_KEYS).issubset(set(dim_map.keys())):
                excluded_missing_style_dna += 1
                continue

            vector = {k: float(dim_map[k]) for k in CANONICAL_DIMENSION_KEYS}
            img_url = f"/api/v1/carpets/{carpet_id}/primary-image" if p_img else None

            museum_meta = {
                "reference_key": meta.reference_key,
                "institution": meta.institution_name,
                "object_title": meta.object_title,
                "museum_object_id": meta.object_identifier,
                "date_or_period": meta.date_display or meta.period,
                "origin_culture": meta.culture,
                "origin_geography": meta.geography,
                "medium_materials": meta.medium,
            }

            candidate = HistoricalCandidateRecord(
                historical_reference_id=h_id,
                reference_key=meta.reference_key,
                institution=meta.institution_name,
                object_title=meta.object_title,
                museum_object_id=meta.object_identifier,
                canonical_source_url=meta.object_url,
                primary_image_url=img_url,
                museum_metadata=museum_meta,
                vector=vector,
                metadata_provenance={
                    "source_type": "HISTORICAL_MUSEUM_REFERENCE",
                    "holding_institution": meta.institution_name,
                    "metadata_assertion": "SOURCE_DOCUMENTED_MUSEUM_METADATA",
                    "reference_key": meta.reference_key,
                },
            )
            eligible_candidates.append(candidate)
            fp_entries.append((h_id, vector))

        fingerprint = compute_corpus_fingerprint(fp_entries)

        accounting = HistoricalCorpusAccounting(
            total_records=total_records,
            eligible_records=len(eligible_candidates),
            excluded_missing_primary_image=excluded_missing_primary_image,
            excluded_missing_style_dna=excluded_missing_style_dna,
            corpus_fingerprint=fingerprint,
        )

        return eligible_candidates, accounting

    @staticmethod
    def load_eligible_corpus_sync(
        db: Session,
    ) -> Tuple[List[HistoricalCandidateRecord], HistoricalCorpusAccounting]:
        all_hist = db.query(HistoricalReferenceMetadataModel).options(
            selectinload(HistoricalReferenceMetadataModel.carpet)
        ).all()
        total_records = len(all_hist)

        primary_images_list = (
            db.query(CarpetImageModel)
            .join(CarpetModel)
            .filter(
                CarpetModel.source_type == CarpetSourceType.HISTORICAL,
                CarpetImageModel.is_primary.is_(True),
            )
            .all()
        )
        primary_images = {img.carpet_id: img for img in primary_images_list}

        profiles_list = (
            db.query(CarpetStyleProfileModel)
            .options(selectinload(CarpetStyleProfileModel.dimensions))
            .join(CarpetModel)
            .filter(
                CarpetModel.source_type == CarpetSourceType.HISTORICAL,
                CarpetStyleProfileModel.algorithm_version == CANONICAL_STYLE_DNA_VERSION,
            )
            .all()
        )
        profiles = {prof.carpet_id: prof for prof in profiles_list}

        eligible_candidates: List[HistoricalCandidateRecord] = []
        fp_entries: List[Tuple[str, Dict[str, float]]] = []

        excluded_missing_primary_image = 0
        excluded_missing_style_dna = 0

        for meta in all_hist:
            h_id = str(meta.id)
            carpet_id = meta.carpet_id

            p_img = primary_images.get(carpet_id)
            p_prof = profiles.get(carpet_id)

            if not p_img:
                excluded_missing_primary_image += 1
                continue

            if not p_prof:
                excluded_missing_style_dna += 1
                continue

            if p_prof.status != StyleProfileStatus.COMPLETE:
                excluded_missing_style_dna += 1
                continue

            dim_map = {d.dimension_key: d.value for d in p_prof.dimensions if d.status == StyleDimensionStatus.AVAILABLE and d.value is not None}
            if len(dim_map) != 9 or not set(CANONICAL_DIMENSION_KEYS).issubset(set(dim_map.keys())):
                excluded_missing_style_dna += 1
                continue

            vector = {k: float(dim_map[k]) for k in CANONICAL_DIMENSION_KEYS}
            img_url = f"/api/v1/carpets/{carpet_id}/primary-image" if p_img else None

            museum_meta = {
                "reference_key": meta.reference_key,
                "institution": meta.institution_name,
                "object_title": meta.object_title,
                "museum_object_id": meta.object_identifier,
                "date_or_period": meta.date_display or meta.period,
                "origin_culture": meta.culture,
                "origin_geography": meta.geography,
                "medium_materials": meta.medium,
            }

            candidate = HistoricalCandidateRecord(
                historical_reference_id=h_id,
                reference_key=meta.reference_key,
                institution=meta.institution_name,
                object_title=meta.object_title,
                museum_object_id=meta.object_identifier,
                canonical_source_url=meta.object_url,
                primary_image_url=img_url,
                museum_metadata=museum_meta,
                vector=vector,
                metadata_provenance={
                    "source_type": "HISTORICAL_MUSEUM_REFERENCE",
                    "holding_institution": meta.institution_name,
                    "metadata_assertion": "SOURCE_DOCUMENTED_MUSEUM_METADATA",
                    "reference_key": meta.reference_key,
                },
            )
            eligible_candidates.append(candidate)
            fp_entries.append((h_id, vector))

        fingerprint = compute_corpus_fingerprint(fp_entries)

        accounting = HistoricalCorpusAccounting(
            total_records=total_records,
            eligible_records=len(eligible_candidates),
            excluded_missing_primary_image=excluded_missing_primary_image,
            excluded_missing_style_dna=excluded_missing_style_dna,
            corpus_fingerprint=fingerprint,
        )

        return eligible_candidates, accounting
