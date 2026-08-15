"""Service layer for side-effect-free Historical Reference queries."""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet_historical_reference import (
    HistoricalSourceRoleEnum,
    HistoricalReferenceMetadataModel
)
from app.domain.common.readiness import derive_style_dna_readiness
from app.domain.carpet_catalog.schemas import PrimaryImageSummary
from app.domain.historical_reference.exceptions import HistoricalReferenceNotFoundError
from app.domain.historical_reference.repository import HistoricalReferenceRepository
from app.domain.historical_reference.schemas import (
    HistoricalReferenceSummary,
    HistoricalReferenceDetailRead,
    HistoricalReferenceSourceRead,
    HistoricalReferenceListResponse,
    HistoricalReferenceMetaResponse
)


class HistoricalReferenceService:
    """Service layer for side-effect-free historical reference queries."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = HistoricalReferenceRepository(session)

    async def list_historical_references(
        self,
        limit: int = 20,
        offset: int = 0,
        institution: Optional[str] = None,
        culture: Optional[str] = None,
        period: Optional[str] = None,
        dynasty_or_tradition: Optional[str] = None,
        department: Optional[str] = None
    ) -> HistoricalReferenceListResponse:
        records, total_count = await self.repo.list_historical_references(
            limit=limit,
            offset=offset,
            institution=institution,
            culture=culture,
            period=period,
            dynasty_or_tradition=dynasty_or_tradition,
            department=department
        )
        summaries = [HistoricalReferenceSummary.model_validate(r) for r in records]
        return HistoricalReferenceListResponse(
            total_count=total_count,
            references=summaries
        )

    async def get_historical_reference_detail(self, identifier: str) -> HistoricalReferenceDetailRead:
        record = await self.repo.get_historical_reference_by_id_or_key(identifier)
        if not record:
            raise HistoricalReferenceNotFoundError(f"Historical reference not found: {identifier}")

        primary_image = await self.repo.get_primary_image(record.carpet_id)
        current_profile = await self.repo.get_current_style_profile(record.carpet_id)

        readiness = derive_style_dna_readiness(primary_image, current_profile)

        primary_img_summary = None
        if primary_image:
            primary_img_summary = PrimaryImageSummary(
                image_id=primary_image.id,
                file_path=primary_image.storage_key,
                width=primary_image.width_px,
                height=primary_image.height_px
            )

        # Sort and group source links
        primary_link = None
        supporting_links = []

        for sl in record.source_links:
            if sl.source_role == HistoricalSourceRoleEnum.PRIMARY_OBJECT_RECORD:
                primary_link = sl
            else:
                supporting_links.append(sl)

        # Sort supporting links deterministically by source_key ASC
        supporting_links.sort(key=lambda sl: sl.source.source_key)

        primary_source_read = HistoricalReferenceSourceRead(
            id=primary_link.id,
            source_id=primary_link.source_id,
            source_role=primary_link.source_role,
            source_key=primary_link.source.source_key,
            title=primary_link.source.title,
            citation_text=primary_link.source.citation_text,
            source_type=primary_link.source.source_type.value,
            locator=primary_link.locator,
            source_note=primary_link.source_note
        )

        supporting_sources_read = [
            HistoricalReferenceSourceRead(
                id=sl.id,
                source_id=sl.source_id,
                source_role=sl.source_role,
                source_key=sl.source.source_key,
                title=sl.source.title,
                citation_text=sl.source.citation_text,
                source_type=sl.source.source_type.value,
                locator=sl.locator,
                source_note=sl.source_note
            )
            for sl in supporting_links
        ]

        return HistoricalReferenceDetailRead(
            id=record.id,
            carpet_id=record.carpet_id,
            reference_key=record.reference_key,
            institution_name=record.institution_name,
            object_identifier=record.object_identifier,
            accession_number=record.accession_number,
            object_title=record.object_title,
            culture=record.culture,
            period=record.period,
            dynasty_or_tradition=record.dynasty_or_tradition,
            date_display=record.date_display,
            date_start_year=record.date_start_year,
            date_end_year=record.date_end_year,
            geography=record.geography,
            medium=record.medium,
            dimensions_text=record.dimensions_text,
            department=record.department,
            credit_line=record.credit_line,
            object_url=record.object_url,
            source_image_url=record.source_image_url,
            rights_statement=record.rights_statement,
            open_access=record.open_access,
            curation_note=record.curation_note,
            schema_version=record.schema_version,
            primary_source=primary_source_read,
            supporting_sources=supporting_sources_read,
            primary_image=primary_img_summary,
            style_dna_readiness=readiness,
            created_at=record.created_at,
            updated_at=record.updated_at
        )

    @staticmethod
    def get_meta_historical_references() -> HistoricalReferenceMetaResponse:
        return HistoricalReferenceMetaResponse()
