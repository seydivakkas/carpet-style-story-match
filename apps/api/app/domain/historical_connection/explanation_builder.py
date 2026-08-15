"""Pure explanation builder for Historical Connection Engine v1."""
from typing import List, Optional, Any
from app.db.models.carpet_historical_connection import HistoricalConnectionStatusEnum
from app.db.models.carpet_historical_reference import HistoricalSourceRoleEnum
from app.domain.historical_reference.schemas import HistoricalReferenceSourceRead
from app.domain.historical_connection.constants import (
    HISTORICAL_CONNECTION_LEVEL_LABELS,
    DETERMINISTIC_HISTORICAL_DISCLAIMER,
    PARTIAL_COVERAGE_NOTE
)
from app.domain.historical_connection.schemas import (
    HistoricalConnectionExplanationRead,
    HistoricalConnectionClosestDimensionRead,
    HistoricalConnectionMainDifferenceRead,
    HistoricalConnectionReferenceContextRead
)


class HistoricalConnectionExplanationBuilder:
    """Pure explanation builder for deterministic historical connection reports."""

    CANONICAL_INDEX = {
        "color_energy": 0,
        "color_diversity": 1,
        "contrast": 2,
        "warmth": 3,
        "visual_complexity": 4,
        "structural_order": 5,
        "rhythm_repetition": 6,
        "focal_strength": 7,
        "form_language": 8
    }

    @classmethod
    def build_explanation(
        cls,
        connection_result: Any,
        dimension_models: List[Any],
        historical_reference_metadata: Any,
        source_links: List[Any]
    ) -> HistoricalConnectionExplanationRead:
        level_label = (
            HISTORICAL_CONNECTION_LEVEL_LABELS.get(connection_result.connection_level)
            if connection_result.connection_level else None
        )

        comparable_dims = [d for d in dimension_models if getattr(d, "comparable", False)]

        # Top 3 closest dimensions (similarity DESC, tie canonical index ASC)
        sorted_closest = sorted(
            comparable_dims,
            key=lambda d: (-getattr(d, "similarity", 0.0), cls.CANONICAL_INDEX.get(d.dimension_key, 99))
        )
        closest_reads = [
            HistoricalConnectionClosestDimensionRead(
                dimension_key=d.dimension_key,
                similarity=float(d.similarity),
                target_value=float(d.target_value),
                reference_value=float(d.reference_value)
            )
            for d in sorted_closest[:3]
        ]

        # Top 2 main differences (difference DESC, tie canonical index ASC)
        sorted_diffs = sorted(
            comparable_dims,
            key=lambda d: (-getattr(d, "difference", 0.0), cls.CANONICAL_INDEX.get(d.dimension_key, 99))
        )
        main_diff_reads = [
            HistoricalConnectionMainDifferenceRead(
                dimension_key=d.dimension_key,
                difference=float(d.difference),
                target_value=float(d.target_value),
                reference_value=float(d.reference_value)
            )
            for d in sorted_diffs[:2]
        ]

        # Low confidence annotations
        low_confidence = [
            d.dimension_key for d in dimension_models
            if getattr(d, "target_status", "") == "LOW_CONFIDENCE" or getattr(d, "reference_status", "") == "LOW_CONFIDENCE"
        ]

        # Map reference context
        meta = historical_reference_metadata
        ref_context = HistoricalConnectionReferenceContextRead(
            reference_id=meta.id,
            reference_key=meta.reference_key,
            institution_name=meta.institution_name,
            object_identifier=meta.object_identifier,
            accession_number=meta.accession_number,
            object_title=meta.object_title,
            culture=meta.culture,
            period=meta.period,
            dynasty_or_tradition=meta.dynasty_or_tradition,
            date_display=meta.date_display,
            date_start_year=meta.date_start_year,
            date_end_year=meta.date_end_year,
            geography=meta.geography,
            medium=meta.medium,
            dimensions_text=meta.dimensions_text,
            department=meta.department,
            credit_line=meta.credit_line,
            object_url=meta.object_url,
            source_image_url=meta.source_image_url,
            rights_statement=meta.rights_statement,
            open_access=meta.open_access
        )

        # Separate primary and supporting source links
        primary_link = None
        supporting_links = []

        for sl in source_links:
            if sl.source_role == HistoricalSourceRoleEnum.PRIMARY_OBJECT_RECORD:
                primary_link = sl
            else:
                supporting_links.append(sl)

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

        coverage_note = (
            PARTIAL_COVERAGE_NOTE
            if connection_result.status == HistoricalConnectionStatusEnum.PARTIAL
            else None
        )

        return HistoricalConnectionExplanationRead(
            connection_level_label_tr=level_label,
            closest_dimensions=closest_reads,
            main_differences=main_diff_reads,
            low_confidence_dimensions=low_confidence,
            reference_context=ref_context,
            primary_source=primary_source_read,
            supporting_sources=supporting_sources_read,
            disclaimer=DETERMINISTIC_HISTORICAL_DISCLAIMER,
            coverage_note=coverage_note
        )
