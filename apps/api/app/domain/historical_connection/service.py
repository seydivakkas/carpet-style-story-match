"""Service layer for Historical Connection Engine v1."""
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet import CarpetSourceType
from app.db.models.carpet_style_profile import StyleProfileStatus
from app.db.models.carpet_historical_connection import (
    HistoricalConnectionResultModel,
    HistoricalConnectionDimensionModel
)
from app.domain.historical_connection.constants import HISTORICAL_CONNECTION_VERSION
from app.domain.historical_connection.exceptions import (
    HistoricalConnectionNotFoundError,
    HistoricalConnectionTargetProfileNotFoundError,
    HistoricalConnectionTargetProfileFailedError,
    HistoricalConnectionInvalidTargetTypeError,
    HistoricalConnectionReferenceNotFoundError,
    HistoricalConnectionReferenceImageRequiredError,
    HistoricalConnectionReferenceProfileRequiredError,
    HistoricalConnectionReferenceProfileFailedError,
    HistoricalConnectionStyleVersionMismatchError
)
from app.domain.historical_connection.engine import HistoricalConnectionEngine
from app.domain.historical_connection.explanation_builder import HistoricalConnectionExplanationBuilder
from app.domain.historical_connection.repository import HistoricalConnectionRepository
from app.domain.historical_connection.schemas import (
    HistoricalConnectionCreateInput,
    HistoricalConnectionDimensionRead,
    HistoricalConnectionDetailRead,
    HistoricalConnectionSummaryRead,
    HistoricalConnectionListResponse,
    HistoricalConnectionMetaResponse
)


class HistoricalConnectionService:
    """Service layer for historical connection evaluation, persistence, and queries."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = HistoricalConnectionRepository(session)

    async def create_historical_connection(
        self,
        input_data: HistoricalConnectionCreateInput
    ) -> HistoricalConnectionDetailRead:
        # 1. Resolve & validate target style profile
        target_profile = await self.repo.get_style_profile_by_id(input_data.target_style_profile_id)
        if not target_profile:
            raise HistoricalConnectionTargetProfileNotFoundError(
                f"Target Style DNA profile not found: {input_data.target_style_profile_id}"
            )

        if target_profile.status == StyleProfileStatus.FAILED:
            raise HistoricalConnectionTargetProfileFailedError(
                f"Target Style DNA profile {input_data.target_style_profile_id} has status FAILED"
            )

        # 2. Reject HISTORICAL target carpet
        target_carpet = await self.repo.get_carpet_by_id(target_profile.carpet_id)
        if target_carpet and target_carpet.source_type == CarpetSourceType.HISTORICAL:
            raise HistoricalConnectionInvalidTargetTypeError(
                f"Target carpet {target_profile.carpet_id} has source_type HISTORICAL. Historical targets are rejected."
            )

        # 3. Resolve & validate historical reference metadata
        meta = await self.repo.get_historical_reference(input_data.historical_reference_id)
        if not meta:
            raise HistoricalConnectionReferenceNotFoundError(
                f"Historical reference not found: {input_data.historical_reference_id}"
            )

        # 4. Resolve & validate primary local image
        primary_image = await self.repo.get_primary_image(meta.carpet_id)
        if not primary_image:
            raise HistoricalConnectionReferenceImageRequiredError(
                f"Historical reference '{meta.reference_key}' lacks a primary local image."
            )

        # 5. Resolve & validate current reference style profile
        ref_profile = await self.repo.get_current_style_profile(meta.carpet_id)
        if not ref_profile:
            raise HistoricalConnectionReferenceProfileRequiredError(
                f"Historical reference '{meta.reference_key}' primary image lacks a Style DNA profile."
            )

        if ref_profile.status == StyleProfileStatus.FAILED:
            raise HistoricalConnectionReferenceProfileFailedError(
                f"Historical reference '{meta.reference_key}' Style DNA profile status is FAILED."
            )

        # 6. Validate algorithm version compatibility
        if target_profile.algorithm_version != ref_profile.algorithm_version:
            raise HistoricalConnectionStyleVersionMismatchError(
                f"Style DNA algorithm version mismatch: target='{target_profile.algorithm_version}', reference='{ref_profile.algorithm_version}'"
            )

        # 7. Check idempotency
        existing_result = await self.repo.get_by_idempotency_key(
            target_profile.id,
            ref_profile.id,
            HISTORICAL_CONNECTION_VERSION
        )
        if existing_result:
            return self._build_detail_read(existing_result)

        # 8. Evaluate comparison pure engine
        evaluation = HistoricalConnectionEngine.evaluate(
            target_dimensions=target_profile.dimensions,
            reference_dimensions=ref_profile.dimensions
        )

        # 9. Create DB models
        result_id = uuid.uuid4()
        result_model = HistoricalConnectionResultModel(
            id=result_id,
            target_carpet_id=target_profile.carpet_id,
            target_style_profile_id=target_profile.id,
            historical_carpet_id=meta.carpet_id,
            historical_reference_metadata_id=meta.id,
            historical_style_profile_id=ref_profile.id,
            connection_version=HISTORICAL_CONNECTION_VERSION,
            status=evaluation["status"],
            not_available_reason=evaluation["not_available_reason"],
            style_similarity=evaluation["style_similarity"],
            connection_level=evaluation["connection_level"],
            comparable_dimension_count=evaluation["comparable_dimension_count"],
            dimension_coverage=evaluation["dimension_coverage"]
        )

        dimension_models = [
            HistoricalConnectionDimensionModel(
                id=uuid.uuid4(),
                historical_connection_id=result_id,
                dimension_key=d["dimension_key"],
                target_value=d["target_value"],
                target_status=d["target_status"],
                target_confidence=d["target_confidence"],
                reference_value=d["reference_value"],
                reference_status=d["reference_status"],
                reference_confidence=d["reference_confidence"],
                difference=d["difference"],
                similarity=d["similarity"],
                comparable=d["comparable"]
            )
            for d in evaluation["dimensions"]
        ]

        saved_result = await self.repo.create_connection_result(result_model, dimension_models)
        return self._build_detail_read(saved_result)

    async def get_historical_connection_detail(self, connection_id: uuid.UUID) -> HistoricalConnectionDetailRead:
        result = await self.repo.get_by_id(connection_id)
        if not result:
            raise HistoricalConnectionNotFoundError(f"Historical connection result not found: {connection_id}")
        return self._build_detail_read(result)

    async def list_historical_connections(
        self,
        limit: int = 20,
        offset: int = 0,
        target_style_profile_id: Optional[uuid.UUID] = None,
        historical_reference_id: Optional[str] = None
    ) -> HistoricalConnectionListResponse:
        records, total_count = await self.repo.list_connection_results(
            limit=limit,
            offset=offset,
            target_style_profile_id=target_style_profile_id,
            historical_reference_id=historical_reference_id
        )
        summaries = [HistoricalConnectionSummaryRead.model_validate(r) for r in records]
        return HistoricalConnectionListResponse(
            total_count=total_count,
            connections=summaries
        )

    @staticmethod
    def get_meta_historical_connections() -> HistoricalConnectionMetaResponse:
        return HistoricalConnectionMetaResponse()

    @classmethod
    def _build_detail_read(cls, result: HistoricalConnectionResultModel) -> HistoricalConnectionDetailRead:
        # Enforce canonical D1..D9 ordering
        canonical_map = {d.dimension_key: d for d in result.dimensions}
        ordered_dims = [
            canonical_map[key] for key in HistoricalConnectionEngine.CANONICAL_DIMENSIONS
            if key in canonical_map
        ]

        explanation_read = HistoricalConnectionExplanationBuilder.build_explanation(
            connection_result=result,
            dimension_models=ordered_dims,
            historical_reference_metadata=result.historical_reference_metadata,
            source_links=result.historical_reference_metadata.source_links
        )

        dim_reads = [HistoricalConnectionDimensionRead.model_validate(d) for d in ordered_dims]

        return HistoricalConnectionDetailRead(
            id=result.id,
            target_carpet_id=result.target_carpet_id,
            target_style_profile_id=result.target_style_profile_id,
            historical_carpet_id=result.historical_carpet_id,
            historical_reference_metadata_id=result.historical_reference_metadata_id,
            historical_style_profile_id=result.historical_style_profile_id,
            connection_version=result.connection_version,
            status=result.status,
            not_available_reason=result.not_available_reason,
            style_similarity=result.style_similarity,
            connection_level=result.connection_level,
            comparable_dimension_count=result.comparable_dimension_count,
            dimension_coverage=result.dimension_coverage,
            dimensions=dim_reads,
            explanation=explanation_read,
            created_at=result.created_at
        )
