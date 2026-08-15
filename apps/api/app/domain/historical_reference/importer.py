"""Importer class for Historical Reference Collection v1."""
from typing import Dict, List, Any
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.motif_knowledge import SourceTypeEnum
from app.db.models.carpet_historical_reference import (
    HistoricalSourceRoleEnum,
    HistoricalReferenceMetadataModel,
    HistoricalReferenceSourceModel
)
from app.domain.historical_reference.constants import HISTORICAL_REFERENCE_SCHEMA_VERSION
from app.domain.historical_reference.exceptions import (
    HistoricalReferenceInvalidSchemaVersionError,
    HistoricalReferencePrimarySourceRequiredError,
    HistoricalReferenceMultiplePrimarySourcesError,
    HistoricalReferenceInvalidPrimarySourceTypeError,
    HistoricalReferenceUnknownSourceError,
    HistoricalReferenceIdentityRequiredError,
    HistoricalReferenceDateRangeInvalidError,
    HistoricalReferenceConflictError,
    HistoricalReferenceObjectConflictError
)
from app.domain.historical_reference.repository import HistoricalReferenceRepository
from app.domain.historical_reference.schemas import HistoricalReferenceImportDataset, HistoricalReferenceInput


class HistoricalReferenceImporter:
    """Importer for historical reference curation datasets with transaction management & dry-run."""

    VALID_PRIMARY_SOURCE_TYPES = {
        SourceTypeEnum.MUSEUM_OBJECT,
        SourceTypeEnum.ARCHIVE_RECORD
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = HistoricalReferenceRepository(session)

    async def import_dataset(
        self,
        dataset: HistoricalReferenceImportDataset,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        # 1. Schema version validation
        if dataset.schema_version != HISTORICAL_REFERENCE_SCHEMA_VERSION:
            raise HistoricalReferenceInvalidSchemaVersionError(
                f"Invalid schema_version '{dataset.schema_version}'. Expected '{HISTORICAL_REFERENCE_SCHEMA_VERSION}'"
            )

        imported_count = 0
        skipped_count = 0

        # Actions to perform on commit if valid
        planned_actions: List[Dict[str, Any]] = []

        for item in dataset.references:
            # 2. Required identity validation
            if (
                not item.reference_key
                or not item.institution_name
                or not item.object_identifier
                or not item.object_title
            ):
                raise HistoricalReferenceIdentityRequiredError(
                    f"Reference item missing required identity fields (key={item.reference_key})"
                )

            # 3. Date range validation
            if (
                item.date_start_year is not None
                and item.date_end_year is not None
                and item.date_start_year > item.date_end_year
            ):
                raise HistoricalReferenceDateRangeInvalidError(
                    f"Invalid date range for '{item.reference_key}': {item.date_start_year} > {item.date_end_year}"
                )

            # 4. Primary source validation
            if not item.primary_source_key:
                raise HistoricalReferencePrimarySourceRequiredError(
                    f"Historical reference '{item.reference_key}' requires a primary_source_key"
                )

            primary_src = await self.repo.get_curated_source_by_key(item.primary_source_key)
            if not primary_src:
                raise HistoricalReferenceUnknownSourceError(
                    f"Unknown primary source_key '{item.primary_source_key}' for reference '{item.reference_key}'"
                )

            if primary_src.source_type not in self.VALID_PRIMARY_SOURCE_TYPES:
                raise HistoricalReferenceInvalidPrimarySourceTypeError(
                    f"Primary source '{item.primary_source_key}' has type '{primary_src.source_type.value}'. Must be MUSEUM_OBJECT or ARCHIVE_RECORD."
                )

            # 5. Supporting sources resolution
            resolved_supporting = []
            for supp_input in item.supporting_sources:
                supp_src = await self.repo.get_curated_source_by_key(supp_input.source_key)
                if not supp_src:
                    raise HistoricalReferenceUnknownSourceError(
                        f"Unknown supporting source_key '{supp_input.source_key}' for reference '{item.reference_key}'"
                    )
                resolved_supporting.append((supp_src, supp_input.locator, supp_input.source_note))

            # 6. Conflict & Idempotency Check
            existing_by_key = await self.repo.get_by_reference_key(item.reference_key)
            existing_by_object = await self.repo.get_by_institution_and_object_id(
                item.institution_name,
                item.object_identifier
            )

            # Object identity conflict: same (institution, object_id) with different reference_key
            if existing_by_object and existing_by_object.reference_key != item.reference_key:
                raise HistoricalReferenceObjectConflictError(
                    f"Object identifier '{item.object_identifier}' at '{item.institution_name}' is already assigned to reference_key '{existing_by_object.reference_key}'"
                )

            if existing_by_key:
                # Check exact idempotency
                if self._is_exact_duplicate(existing_by_key, item, primary_src, resolved_supporting):
                    skipped_count += 1
                    continue
                else:
                    raise HistoricalReferenceConflictError(
                        f"Conflicting metadata for existing reference_key '{item.reference_key}'"
                    )

            planned_actions.append({
                "input": item,
                "primary_source": primary_src,
                "supporting_sources": resolved_supporting
            })
            imported_count += 1

        if dry_run:
            return {
                "dry_run": True,
                "status": "VALID",
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "total_count": len(dataset.references)
            }

        # Execute DB creation transactionally
        for action in planned_actions:
            item: HistoricalReferenceInput = action["input"]
            primary_src = action["primary_source"]
            supporting_srcs = action["supporting_sources"]

            carpet_model = CarpetModel(
                id=uuid.uuid4(),
                sku=None,
                name=item.object_title,
                description=item.curation_note,
                source_type=CarpetSourceType.HISTORICAL,
                source_reference=item.reference_key,
                is_active=True
            )

            metadata_model = HistoricalReferenceMetadataModel(
                id=uuid.uuid4(),
                reference_key=item.reference_key,
                institution_name=item.institution_name,
                object_identifier=item.object_identifier,
                accession_number=item.accession_number,
                object_title=item.object_title,
                culture=item.culture,
                period=item.period,
                dynasty_or_tradition=item.dynasty_or_tradition,
                date_display=item.date_display,
                date_start_year=item.date_start_year,
                date_end_year=item.date_end_year,
                geography=item.geography,
                medium=item.medium,
                dimensions_text=item.dimensions_text,
                department=item.department,
                credit_line=item.credit_line,
                object_url=item.object_url,
                source_image_url=item.source_image_url,
                rights_statement=item.rights_statement,
                open_access=item.open_access,
                curation_note=item.curation_note,
                schema_version=HISTORICAL_REFERENCE_SCHEMA_VERSION
            )

            source_link_models: List[HistoricalReferenceSourceModel] = [
                HistoricalReferenceSourceModel(
                    id=uuid.uuid4(),
                    source_id=primary_src.id,
                    source_role=HistoricalSourceRoleEnum.PRIMARY_OBJECT_RECORD,
                    locator=None,
                    source_note=None
                )
            ]

            for supp_src, loc, note in supporting_srcs:
                source_link_models.append(
                    HistoricalReferenceSourceModel(
                        id=uuid.uuid4(),
                        source_id=supp_src.id,
                        source_role=HistoricalSourceRoleEnum.SUPPORTING_REFERENCE,
                        locator=loc,
                        source_note=note
                    )
                )

            await self.repo.create_historical_reference(carpet_model, metadata_model, source_link_models)

        await self.session.commit()

        return {
            "dry_run": False,
            "status": "SUCCESS",
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "total_count": len(dataset.references)
        }

    @staticmethod
    def _is_exact_duplicate(
        existing: HistoricalReferenceMetadataModel,
        item: HistoricalReferenceInput,
        primary_src: Any,
        supporting_srcs: List[Any]
    ) -> bool:
        if existing.institution_name != item.institution_name:
            return False
        if existing.object_identifier != item.object_identifier:
            return False
        if existing.object_title != item.object_title:
            return False
        if existing.culture != item.culture:
            return False
        if existing.period != item.period:
            return False
        if existing.dynasty_or_tradition != item.dynasty_or_tradition:
            return False
        if existing.date_display != item.date_display:
            return False
        if existing.date_start_year != item.date_start_year:
            return False
        if existing.date_end_year != item.date_end_year:
            return False

        # Compare primary source link
        primary_links = [sl for sl in existing.source_links if sl.source_role == HistoricalSourceRoleEnum.PRIMARY_OBJECT_RECORD]
        if not primary_links or primary_links[0].source.source_key != primary_src.source_key:
            return False

        # Compare supporting sources count
        supporting_links = [sl for sl in existing.source_links if sl.source_role == HistoricalSourceRoleEnum.SUPPORTING_REFERENCE]
        if len(supporting_links) != len(supporting_srcs):
            return False

        existing_supp_keys = sorted([sl.source.source_key for sl in supporting_links])
        input_supp_keys = sorted([s[0].source_key for s in supporting_srcs])
        if existing_supp_keys != input_supp_keys:
            return False

        return True
