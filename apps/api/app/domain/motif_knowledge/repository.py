"""Repository for Motif Story Knowledge queries."""
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.motif_knowledge import (
    CuratedSourceModel,
    MotifModel,
    MotifStoryClaimModel,
    MotifStoryClaimSourceModel,
    MotifStoryClaimThemeModel,
    MotifStoryStatusEnum,
)
from app.domain.contracts import CANONICAL_NARRATIVE_THEMES


class MotifKnowledgeRepository:
    """Read-only database repository for motif knowledge queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_motifs(
        self,
        limit: int = 20,
        offset: int = 0,
        story_status: Optional[MotifStoryStatusEnum] = None,
        narrative_theme: Optional[str] = None
    ) -> Tuple[List[MotifModel], int]:
        stmt = select(MotifModel).options(
            selectinload(MotifModel.story_claims).selectinload(MotifStoryClaimModel.themes)
        )

        if story_status or narrative_theme:
            stmt = stmt.join(MotifModel.story_claims)
            if story_status:
                stmt = stmt.where(MotifStoryClaimModel.status == story_status)
            if narrative_theme:
                stmt = stmt.join(MotifStoryClaimModel.themes).where(
                    MotifStoryClaimThemeModel.theme_key == narrative_theme
                )

        stmt = stmt.distinct().order_by(MotifModel.motif_key)

        # Count total
        count_stmt = select(func.count(func.distinct(MotifModel.id)))
        if story_status or narrative_theme:
            count_stmt = count_stmt.select_from(MotifModel).join(MotifModel.story_claims)
            if story_status:
                count_stmt = count_stmt.where(MotifStoryClaimModel.status == story_status)
            if narrative_theme:
                count_stmt = count_stmt.join(MotifStoryClaimModel.themes).where(
                    MotifStoryClaimThemeModel.theme_key == narrative_theme
                )
        else:
            count_stmt = count_stmt.select_from(MotifModel)

        total_res = await self.session.execute(count_stmt)
        total_count = total_res.scalar_one()

        res = await self.session.execute(stmt.offset(offset).limit(limit))
        motifs = list(res.scalars().all())

        return motifs, total_count

    async def get_motif_by_id_or_key(self, identifier: str) -> Optional[MotifModel]:
        is_uuid = self._is_valid_uuid(identifier)
        if is_uuid:
            stmt = (
                select(MotifModel)
                .options(selectinload(MotifModel.story_claims).selectinload(MotifStoryClaimModel.themes))
                .where(or_(MotifModel.id == uuid.UUID(identifier), MotifModel.motif_key == identifier))
            )
        else:
            stmt = (
                select(MotifModel)
                .options(selectinload(MotifModel.story_claims).selectinload(MotifStoryClaimModel.themes))
                .where(MotifModel.motif_key == identifier)
            )

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_claims(
        self,
        limit: int = 20,
        offset: int = 0,
        motif_id_or_key: Optional[str] = None,
        status: Optional[MotifStoryStatusEnum] = None,
        narrative_theme: Optional[str] = None
    ) -> Tuple[List[MotifStoryClaimModel], int]:
        stmt = (
            select(MotifStoryClaimModel)
            .options(
                selectinload(MotifStoryClaimModel.motif),
                selectinload(MotifStoryClaimModel.themes),
                selectinload(MotifStoryClaimModel.sources).selectinload(MotifStoryClaimSourceModel.source)
            )
        )

        if motif_id_or_key:
            if self._is_valid_uuid(motif_id_or_key):
                stmt = stmt.join(MotifStoryClaimModel.motif).where(
                    or_(MotifModel.id == uuid.UUID(motif_id_or_key), MotifModel.motif_key == motif_id_or_key)
                )
            else:
                stmt = stmt.join(MotifStoryClaimModel.motif).where(MotifModel.motif_key == motif_id_or_key)

        if status:
            stmt = stmt.where(MotifStoryClaimModel.status == status)

        if narrative_theme:
            stmt = stmt.join(MotifStoryClaimModel.themes).where(
                MotifStoryClaimThemeModel.theme_key == narrative_theme
            )

        stmt = stmt.distinct().order_by(MotifStoryClaimModel.claim_key)

        count_stmt = select(func.count(func.distinct(MotifStoryClaimModel.id))).select_from(MotifStoryClaimModel)
        if motif_id_or_key:
            if self._is_valid_uuid(motif_id_or_key):
                count_stmt = count_stmt.join(MotifStoryClaimModel.motif).where(
                    or_(MotifModel.id == uuid.UUID(motif_id_or_key), MotifModel.motif_key == motif_id_or_key)
                )
            else:
                count_stmt = count_stmt.join(MotifStoryClaimModel.motif).where(MotifModel.motif_key == motif_id_or_key)
        if status:
            count_stmt = count_stmt.where(MotifStoryClaimModel.status == status)
        if narrative_theme:
            count_stmt = count_stmt.join(MotifStoryClaimModel.themes).where(
                MotifStoryClaimThemeModel.theme_key == narrative_theme
            )

        total_res = await self.session.execute(count_stmt)
        total_count = total_res.scalar_one()

        res = await self.session.execute(stmt.offset(offset).limit(limit))
        claims = list(res.scalars().all())

        return claims, total_count

    async def get_claim_by_id_or_key(self, identifier: str) -> Optional[MotifStoryClaimModel]:
        is_uuid = self._is_valid_uuid(identifier)
        if is_uuid:
            stmt = (
                select(MotifStoryClaimModel)
                .options(
                    selectinload(MotifStoryClaimModel.motif),
                    selectinload(MotifStoryClaimModel.themes),
                    selectinload(MotifStoryClaimModel.sources).selectinload(MotifStoryClaimSourceModel.source)
                )
                .where(or_(MotifStoryClaimModel.id == uuid.UUID(identifier), MotifStoryClaimModel.claim_key == identifier))
            )
        else:
            stmt = (
                select(MotifStoryClaimModel)
                .options(
                    selectinload(MotifStoryClaimModel.motif),
                    selectinload(MotifStoryClaimModel.themes),
                    selectinload(MotifStoryClaimModel.sources).selectinload(MotifStoryClaimSourceModel.source)
                )
                .where(MotifStoryClaimModel.claim_key == identifier)
            )

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_source_by_id_or_key(self, identifier: str) -> Optional[CuratedSourceModel]:
        is_uuid = self._is_valid_uuid(identifier)
        if is_uuid:
            stmt = select(CuratedSourceModel).where(
                or_(CuratedSourceModel.id == uuid.UUID(identifier), CuratedSourceModel.source_key == identifier)
            )
        else:
            stmt = select(CuratedSourceModel).where(CuratedSourceModel.source_key == identifier)

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    def _is_valid_uuid(val: str) -> bool:
        try:
            uuid.UUID(val)
            return True
        except ValueError:
            return False
