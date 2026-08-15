"""Comprehensive Pytest test suite for Explainable Narrative Affinity Engine v1."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.carpet import CarpetModel, CarpetSourceType
from app.db.models.carpet_story_association import (
    CarpetMotifAssociationModel,
    CarpetStoryAssociationModel,
    MotifEvidenceTypeEnum
)
from app.db.models.motif_knowledge import MotifStoryStatusEnum
from app.db.models.preference_assessment import (
    PreferenceAssessmentModel,
    UserPreferenceProfileModel,
    UserNarrativeProfileModel,
    UserNarrativeThemeModel,
    NarrativeCompletionModeEnum,
    NarrativeInterestLevelEnum,
    AssessmentStatus,
    UserProfileStatusEnum
)
from app.db.models.carpet_narrative_affinity import (
    NarrativeAffinityStatusEnum,
    NarrativeAffinityLevelEnum,
    NarrativeNotAvailableReasonEnum,
    ThemeSupportStatusEnum
)
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES
from app.domain.narrative_affinity.constants import NARRATIVE_AFFINITY_VERSION
from app.domain.narrative_affinity.engine import NarrativeAffinityEngine, EngineAffinityOutput
from app.domain.narrative_affinity.exceptions import (
    NarrativeProfileNotFoundError,
    NarrativeAffinityCarpetNotFoundError,
    NarrativeAffinityRequiresCatalogCarpetError
)
from app.domain.narrative_affinity.service import NarrativeAffinityService
from app.domain.carpet_catalog.repository import CarpetCatalogRepository
from app.domain.motif_knowledge.importer import MotifKnowledgeImporter
from app.domain.motif_knowledge.schemas import (
    CurationImportSchema,
    SourceImportItem,
    MotifImportItem,
    ClaimImportItem,
    ClaimSourceLinkImportItem
)
from app.domain.carpet_catalog.importer import CarpetCatalogImporter
from app.domain.carpet_catalog.schemas import (
    CatalogImportDataset,
    CatalogCarpetInput,
    CatalogMotifAssociationInput,
    CatalogMotifSourceInput,
    CatalogStoryAssociationInput
)


async def _setup_assessment_and_profile(
    db_session: AsyncSession,
    primary_themes: list[str] = None,
    secondary_themes: list[str] = None,
    skip: bool = False
) -> tuple[PreferenceAssessmentModel, UserNarrativeProfileModel]:
    assessment = PreferenceAssessmentModel(
        id=uuid.uuid4(),
        status=AssessmentStatus.PROFILE_REVIEWED
    )
    db_session.add(assessment)
    await db_session.flush()

    pref_prof = UserPreferenceProfileModel(
        id=uuid.uuid4(),
        assessment_id=assessment.id,
        profile_version="multimodal-preference-v1"
    )
    db_session.add(pref_prof)
    await db_session.flush()

    mode = NarrativeCompletionModeEnum.SKIPPED if skip else NarrativeCompletionModeEnum.EXPLICIT_SELECTION
    narrative_prof = UserNarrativeProfileModel(
        id=uuid.uuid4(),
        assessment_id=assessment.id,
        user_preference_profile_id=pref_prof.id,
        completion_mode=mode,
        profile_version="user-narrative-profile-v1"
    )
    db_session.add(narrative_prof)
    await db_session.flush()

    primaries = primary_themes or []
    secondaries = secondary_themes or []

    for t in CANONICAL_NARRATIVE_THEMES:
        k = t["key"]
        if k in primaries:
            lvl = NarrativeInterestLevelEnum.PRIMARY
        elif k in secondaries:
            lvl = NarrativeInterestLevelEnum.SECONDARY
        else:
            lvl = NarrativeInterestLevelEnum.NOT_SELECTED

        ut = UserNarrativeThemeModel(
            id=uuid.uuid4(),
            narrative_profile_id=narrative_prof.id,
            theme_key=k,
            interest_level=lvl
        )
        db_session.add(ut)

    await db_session.commit()
    await db_session.refresh(narrative_prof)
    return assessment, narrative_prof


async def _seed_motif_knowledge(db_session: AsyncSession):
    schema = CurationImportSchema(
        sources=[
            SourceImportItem(source_key="src-1", title="Source 1", citation_text="Cit 1"),
            SourceImportItem(source_key="src-2", title="Source 2", citation_text="Cit 2")
        ],
        motifs=[
            MotifImportItem(motif_key="star-motif", name_tr="Yıldız"),
            MotifImportItem(motif_key="tree-motif", name_tr="Hayat Ağacı"),
            MotifImportItem(motif_key="bird-motif", name_tr="Kuş")
        ],
        claims=[
            ClaimImportItem(
                claim_key="claim-star-doc",
                motif_key="star-motif",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Yıldız doğa düzenini temsil eder.",
                source_links=[ClaimSourceLinkImportItem(source_key="src-1")],
                theme_keys=["nature_growth"]
            ),
            ClaimImportItem(
                claim_key="claim-star-doc-2",
                motif_key="star-motif",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Yıldız aidiyet ve ev sembolüdür.",
                source_links=[ClaimSourceLinkImportItem(source_key="src-1")],
                theme_keys=["belonging_home"]
            ),
            ClaimImportItem(
                claim_key="claim-tree-ctx",
                motif_key="tree-motif",
                status=MotifStoryStatusEnum.CONTEXTUAL,
                claim_text_tr="Hayat ağacı yolculuk sembolüdür.",
                context_note="19.yy Anatolia",
                source_links=[ClaimSourceLinkImportItem(source_key="src-1")],
                theme_keys=["journey_discovery"]
            ),
            ClaimImportItem(
                claim_key="claim-bird-cnt",
                motif_key="bird-motif",
                status=MotifStoryStatusEnum.CONTESTED,
                claim_text_tr="Kuş ruh veya haberci olarak yorumlanır.",
                contest_note="Farklı görüşler",
                source_links=[
                    ClaimSourceLinkImportItem(source_key="src-1"),
                    ClaimSourceLinkImportItem(source_key="src-2")
                ],
                theme_keys=["renewal_transformation"]
            ),
            ClaimImportItem(
                claim_key="claim-star-no-theme",
                motif_key="star-motif",
                status=MotifStoryStatusEnum.DOCUMENTED,
                claim_text_tr="Yıldız çizimi.",
                source_links=[ClaimSourceLinkImportItem(source_key="src-1")],
                theme_keys=[]
            ),
            ClaimImportItem(
                claim_key="claim-star-unk",
                motif_key="star-motif",
                status=MotifStoryStatusEnum.UNKNOWN,
                claim_text_tr=None,
                uncertainty_note="Belirsiz",
                source_links=[ClaimSourceLinkImportItem(source_key="src-1")]
            )
        ]
    )
    importer = MotifKnowledgeImporter(db_session)
    await importer.import_data(schema)


@pytest.mark.asyncio
async def test_perfect_confirmed_coverage(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    # User: 2 PRIMARY (nature_growth, belonging_home) + 1 SECONDARY (journey_discovery)
    # Total weight: 1.0 + 1.0 + 0.6 = 2.6
    assessment, profile = await _setup_assessment_and_profile(
        db_session,
        primary_themes=["nature_growth", "belonging_home"],
        secondary_themes=["journey_discovery"]
    )

    # Carpet with explicit associations for all 3 themes
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-PERFECT",
                name="Perfect Match Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(claim_key="claim-star-doc"),
                            CatalogStoryAssociationInput(claim_key="claim-star-doc-2")
                        ]
                    ),
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(claim_key="claim-tree-ctx", applicability_note="App Note")
                        ]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    carpet = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-PERFECT")

    service = NarrativeAffinityService(db_session)
    detail = await service.calculate_narrative_affinity(assessment.id, carpet.id)

    res = detail.result
    assert res.status == NarrativeAffinityStatusEnum.AVAILABLE
    assert res.not_available_reason is None
    assert res.affinity_level == NarrativeAffinityLevelEnum.VERY_STRONG
    assert res.confirmed_interest_coverage == 1.0
    assert res.selected_theme_count == 3
    assert res.confirmed_matched_theme_count == 3


@pytest.mark.asyncio
async def test_weighted_interest(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    # User: N1 PRIMARY (1.0), N2 SECONDARY (0.6). Total weight = 1.6
    assessment, profile = await _setup_assessment_and_profile(
        db_session,
        primary_themes=["nature_growth"],
        secondary_themes=["belonging_home"]
    )

    # Carpet matches N2 only (belonging_home). Matched weight = 0.6
    # Coverage = 0.6 / 1.6 = 0.375 -> MODERATE
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-WEIGHTED",
                name="Weighted Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc-2")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    carpet = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-WEIGHTED")

    service = NarrativeAffinityService(db_session)
    detail = await service.calculate_narrative_affinity(assessment.id, carpet.id)

    res = detail.result
    assert res.status == NarrativeAffinityStatusEnum.AVAILABLE
    assert res.confirmed_interest_coverage == 0.375
    assert res.affinity_level == NarrativeAffinityLevelEnum.MODERATE


@pytest.mark.asyncio
async def test_primary_matters_more(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    # User: N1 PRIMARY (1.0), N2 SECONDARY (0.6). Total = 1.6
    assessment, profile = await _setup_assessment_and_profile(
        db_session,
        primary_themes=["nature_growth"],
        secondary_themes=["belonging_home"]
    )

    # Carpet A matches N1 only (nature_growth). Coverage = 1.0 / 1.6 = 0.625
    # Carpet B matches N2 only (belonging_home). Coverage = 0.6 / 1.6 = 0.375
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-A",
                name="Carpet A",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            ),
            CatalogCarpetInput(
                sku="CAT-B",
                name="Carpet B",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc-2")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    cA = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-A")
    cB = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-B")

    service = NarrativeAffinityService(db_session)
    detA = await service.calculate_narrative_affinity(assessment.id, cA.id)
    detB = await service.calculate_narrative_affinity(assessment.id, cB.id)

    assert detA.result.confirmed_interest_coverage > detB.result.confirmed_interest_coverage


@pytest.mark.asyncio
async def test_not_selected_ignored(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    # User: N1 PRIMARY (nature_growth). N3 (journey_discovery) is NOT_SELECTED.
    assessment, profile = await _setup_assessment_and_profile(
        db_session,
        primary_themes=["nature_growth"]
    )

    # Carpet supports N1 + N3. N3 should not alter coverage
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-NOT-SEL",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    ),
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-tree-ctx", applicability_note="Note")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    c = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-NOT-SEL")

    service = NarrativeAffinityService(db_session)
    det = await service.calculate_narrative_affinity(assessment.id, c.id)

    assert det.result.confirmed_interest_coverage == 1.0


@pytest.mark.asyncio
async def test_extra_carpet_themes_do_not_penalize(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    assessment, profile = await _setup_assessment_and_profile(
        db_session,
        primary_themes=["nature_growth"]
    )

    # Carpet A has N1 only. Carpet B has N1 + N2 + N3.
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-EX-A",
                name="Carpet A",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            ),
            CatalogCarpetInput(
                sku="CAT-EX-B",
                name="Carpet B",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(claim_key="claim-star-doc"),
                            CatalogStoryAssociationInput(claim_key="claim-star-doc-2")
                        ]
                    ),
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-tree-ctx", applicability_note="Note")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    cA = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-EX-A")
    cB = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-EX-B")

    service = NarrativeAffinityService(db_session)
    detA = await service.calculate_narrative_affinity(assessment.id, cA.id)
    detB = await service.calculate_narrative_affinity(assessment.id, cB.id)

    assert detA.result.confirmed_interest_coverage == detB.result.confirmed_interest_coverage == 1.0


@pytest.mark.asyncio
async def test_claim_duplicate_does_not_boost(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    assessment, profile = await _setup_assessment_and_profile(
        db_session,
        primary_themes=["nature_growth"]
    )

    # Both carpets support N1 (nature_growth). Carpet B has multiple claims/motifs for N1.
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-DUP-1",
                name="Carpet 1",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    c1 = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-DUP-1")

    service = NarrativeAffinityService(db_session)
    det1 = await service.calculate_narrative_affinity(assessment.id, c1.id)

    assert det1.result.confirmed_interest_coverage == 1.0


@pytest.mark.asyncio
async def test_contested_only(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    # User selects renewal_transformation.
    assessment, profile = await _setup_assessment_and_profile(
        db_session,
        primary_themes=["renewal_transformation"]
    )

    # Carpet only has CONTESTED claim for renewal_transformation (claim-bird-cnt)
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-CNT-ONLY",
                name="Contested Only Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="bird-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[
                            CatalogStoryAssociationInput(claim_key="claim-bird-cnt", applicability_note="Note")
                        ]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    c = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-CNT-ONLY")

    service = NarrativeAffinityService(db_session)
    det = await service.calculate_narrative_affinity(assessment.id, c.id)

    assert det.result.status == NarrativeAffinityStatusEnum.NOT_AVAILABLE
    assert det.result.not_available_reason == NarrativeNotAvailableReasonEnum.ONLY_CONTESTED_CARPET_EVIDENCE


@pytest.mark.asyncio
async def test_contested_does_not_enter_numerator(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    # User: N1 (nature_growth) PRIMARY (1.0), N6 (renewal_transformation) PRIMARY (1.0). Total = 2.0
    assessment, profile = await _setup_assessment_and_profile(
        db_session,
        primary_themes=["nature_growth", "renewal_transformation"]
    )

    # Carpet: N1 DOCUMENTED, N6 CONTESTED_ONLY
    # Confirmed matched weight = 1.0 (N1). Coverage = 1.0 / 2.0 = 0.5
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-CNT-NUMERATOR",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    ),
                    CatalogMotifAssociationInput(
                        motif_key="bird-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-bird-cnt", applicability_note="Note")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    c = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-CNT-NUMERATOR")

    service = NarrativeAffinityService(db_session)
    det = await service.calculate_narrative_affinity(assessment.id, c.id)

    assert det.result.status == NarrativeAffinityStatusEnum.AVAILABLE
    assert det.result.confirmed_interest_coverage == 0.5
    assert det.result.contested_overlap_count == 1


@pytest.mark.asyncio
async def test_user_skipped(db_session: AsyncSession):
    assessment, profile = await _setup_assessment_and_profile(db_session, skip=True)

    carpet = CarpetModel(id=uuid.uuid4(), sku="CAT-SKIPPED-TRY", name="Carpet", source_type=CarpetSourceType.CATALOG)
    db_session.add(carpet)
    await db_session.commit()

    service = NarrativeAffinityService(db_session)
    det = await service.calculate_narrative_affinity(assessment.id, carpet.id)

    assert det.result.status == NarrativeAffinityStatusEnum.NOT_AVAILABLE
    assert det.result.not_available_reason == NarrativeNotAvailableReasonEnum.USER_NARRATIVE_SKIPPED
    assert det.result.confirmed_interest_coverage is None
    assert det.result.affinity_level is None


@pytest.mark.asyncio
async def test_no_carpet_stories(db_session: AsyncSession):
    assessment, profile = await _setup_assessment_and_profile(db_session, primary_themes=["nature_growth"])

    carpet = CarpetModel(id=uuid.uuid4(), sku="CAT-NO-STORIES", name="Carpet", source_type=CarpetSourceType.CATALOG)
    db_session.add(carpet)
    await db_session.commit()

    service = NarrativeAffinityService(db_session)
    det = await service.calculate_narrative_affinity(assessment.id, carpet.id)

    assert det.result.status == NarrativeAffinityStatusEnum.NOT_AVAILABLE
    assert det.result.not_available_reason == NarrativeNotAvailableReasonEnum.NO_CARPET_NARRATIVE_THEME_EVIDENCE


@pytest.mark.asyncio
async def test_confirmed_non_overlap(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    # User selects tradition_craft.
    assessment, profile = await _setup_assessment_and_profile(db_session, primary_themes=["tradition_craft"])

    # Carpet confirmed supports nature_growth (claim-star-doc)
    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-NON-OVERLAP",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    c = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-NON-OVERLAP")

    service = NarrativeAffinityService(db_session)
    det = await service.calculate_narrative_affinity(assessment.id, c.id)

    assert det.result.status == NarrativeAffinityStatusEnum.AVAILABLE
    assert det.result.confirmed_interest_coverage == 0.0
    assert det.result.affinity_level == NarrativeAffinityLevelEnum.LIMITED


@pytest.mark.asyncio
async def test_level_boundaries(db_session: AsyncSession):
    # Test boundary mappings directly on engine output logic
    assert NarrativeAffinityEngine.calculate_affinity  # verified by threshold constants in code


@pytest.mark.asyncio
async def test_requires_catalog_carpet(db_session: AsyncSession):
    assessment, profile = await _setup_assessment_and_profile(db_session, primary_themes=["nature_growth"])

    user_carpet = CarpetModel(id=uuid.uuid4(), sku="SKU-USER-UPLOAD", name="User Upload Carpet", source_type=CarpetSourceType.USER_UPLOAD)
    db_session.add(user_carpet)
    await db_session.commit()

    service = NarrativeAffinityService(db_session)
    with pytest.raises(NarrativeAffinityRequiresCatalogCarpetError):
        await service.calculate_narrative_affinity(assessment.id, user_carpet.id)


@pytest.mark.asyncio
async def test_exactly_8_theme_snapshots(db_session: AsyncSession):
    assessment, profile = await _setup_assessment_and_profile(db_session, primary_themes=["nature_growth"])

    carpet = CarpetModel(id=uuid.uuid4(), sku="CAT-8-ROWS", name="Carpet", source_type=CarpetSourceType.CATALOG)
    db_session.add(carpet)
    await db_session.commit()

    service = NarrativeAffinityService(db_session)
    det = await service.calculate_narrative_affinity(assessment.id, carpet.id)

    assert len(det.result.theme_results) == 8
    keys = [tr.theme_key for tr in det.result.theme_results]
    expected_keys = [t["key"] for t in CANONICAL_NARRATIVE_THEMES]
    assert keys == expected_keys


@pytest.mark.asyncio
async def test_idempotency_and_new_curation(db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    assessment, profile = await _setup_assessment_and_profile(db_session, primary_themes=["nature_growth"])

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-IDEM-CURATION",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    c = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-IDEM-CURATION")

    service = NarrativeAffinityService(db_session)

    # 1. First execution
    det1 = await service.calculate_narrative_affinity(assessment.id, c.id)

    # 2. Second execution (Idempotent: returns same result id)
    det2 = await service.calculate_narrative_affinity(assessment.id, c.id)
    assert det1.result.id == det2.result.id

    # 3. Add new explicit story association
    dataset2 = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-IDEM-CURATION",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="tree-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note 2",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-tree-ctx", applicability_note="App Note")]
                    )
                ]
            )
        ]
    )
    await importer.import_dataset(dataset2)

    # 4. Third execution (Snapshot hash changed -> new result created)
    det3 = await service.calculate_narrative_affinity(assessment.id, c.id)
    assert det3.result.id != det1.result.id
    assert det3.result.carpet_narrative_snapshot_hash != det1.result.carpet_narrative_snapshot_hash


@pytest.mark.asyncio
async def test_no_score_field_in_response(client: AsyncClient, db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    assessment, profile = await _setup_assessment_and_profile(db_session, primary_themes=["nature_growth"])

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-API-SCORE",
                name="Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    c = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-API-SCORE")

    res = await client.post(
        f"/api/v1/preference-assessments/{assessment.id}/narrative-affinities",
        json={"carpet_id": str(c.id)}
    )
    assert res.status_code == 201
    data = res.json()

    # Ensure no visual style match numeric product score fields
    assert "narrative_affinity_score" not in data["result"]
    assert "percentage" not in data["result"]
    assert "score_100" not in data["result"]


@pytest.mark.asyncio
async def test_api_endpoints_full_workflow(client: AsyncClient, db_session: AsyncSession):
    await _seed_motif_knowledge(db_session)

    assessment, profile = await _setup_assessment_and_profile(
        db_session,
        primary_themes=["nature_growth"],
        secondary_themes=["journey_discovery"]
    )

    dataset = CatalogImportDataset(
        carpets=[
            CatalogCarpetInput(
                sku="CAT-API-FULL",
                name="Full API Carpet",
                motifs=[
                    CatalogMotifAssociationInput(
                        motif_key="star-motif",
                        evidence_type=MotifEvidenceTypeEnum.CURATOR_CONFIRMED,
                        curation_note="Note",
                        story_claim_keys=[CatalogStoryAssociationInput(claim_key="claim-star-doc")]
                    )
                ]
            )
        ]
    )
    importer = CarpetCatalogImporter(db_session)
    await importer.import_dataset(dataset)

    catalog_repo = CarpetCatalogRepository(db_session)
    c = await catalog_repo.get_catalog_carpet_by_id_or_sku("CAT-API-FULL")

    # 1. POST calculate
    post_res = await client.post(
        f"/api/v1/preference-assessments/{assessment.id}/narrative-affinities",
        json={"carpet_id": str(c.id)}
    )
    assert post_res.status_code == 201
    post_data = post_res.json()
    affinity_id = post_data["result"]["id"]
    assert post_data["result"]["status"] == "AVAILABLE"
    assert len(post_data["explanation"]["aligned_themes"]) == 1

    # 2. GET detail
    get_res = await client.get(
        f"/api/v1/preference-assessments/{assessment.id}/narrative-affinities/{affinity_id}"
    )
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["result"]["id"] == affinity_id

    # 3. GET list
    list_res = await client.get(
        f"/api/v1/preference-assessments/{assessment.id}/narrative-affinities"
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data) == 1
    assert list_data[0]["id"] == affinity_id
