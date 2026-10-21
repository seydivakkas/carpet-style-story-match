"""create motif story knowledge tables

Revision ID: 2026_08_15_010
Revises: 2026_08_15_009
Create Date: 2026-08-15 22:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_010"
down_revision: Union[str, None] = "2026_08_15_009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enum tipleri tek bir kez oluşturulur; tekrar kullanılan alanlar DDL üretmez.
    if op.get_bind().dialect.name == 'postgresql':
        postgresql.ENUM('MUSEUM_OBJECT', 'MUSEUM_CATALOG', 'ACADEMIC_ARTICLE', 'ACADEMIC_BOOK', 'INSTITUTIONAL_PUBLICATION', 'ARCHIVE_RECORD', 'OTHER', name='source_type_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('DOCUMENTED', 'CONTEXTUAL', 'CONTESTED', 'UNKNOWN', name='motif_story_status_enum').create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()

    source_type_enum = postgresql.ENUM(
        'MUSEUM_OBJECT', 'MUSEUM_CATALOG', 'ACADEMIC_ARTICLE', 'ACADEMIC_BOOK',
        'INSTITUTIONAL_PUBLICATION', 'ARCHIVE_RECORD', 'OTHER',
        name='source_type_enum', create_type=False
    )
    source_type_enum.create(bind, checkfirst=True)

    motif_story_status_enum = postgresql.ENUM(
        'DOCUMENTED', 'CONTEXTUAL', 'CONTESTED', 'UNKNOWN',
        name='motif_story_status_enum', create_type=False
    )
    motif_story_status_enum.create(bind, checkfirst=True)

    # 1. curated_sources
    op.create_table(
        'curated_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_key', sa.String(length=100), nullable=False),
        sa.Column('source_type', postgresql.ENUM('MUSEUM_OBJECT', 'MUSEUM_CATALOG', 'ACADEMIC_ARTICLE', 'ACADEMIC_BOOK', 'INSTITUTIONAL_PUBLICATION', 'ARCHIVE_RECORD', 'OTHER', name='source_type_enum', create_type=False), nullable=False, server_default='OTHER'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('citation_text', sa.String(length=1000), nullable=False),
        sa.Column('creator_or_institution', sa.String(length=255), nullable=True),
        sa.Column('publication_year', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('doi', sa.String(length=255), nullable=True),
        sa.Column('isbn', sa.String(length=255), nullable=True),
        sa.Column('rights_note', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_key')
    )
    op.create_index(op.f('ix_curated_sources_source_key'), 'curated_sources', ['source_key'], unique=True)

    # 2. motifs
    op.create_table(
        'motifs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('motif_key', sa.String(length=100), nullable=False),
        sa.Column('name_tr', sa.String(length=255), nullable=False),
        sa.Column('name_en', sa.String(length=255), nullable=True),
        sa.Column('visual_description_tr', sa.String(length=1000), nullable=True),
        sa.Column('visual_description_en', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('motif_key')
    )
    op.create_index(op.f('ix_motifs_motif_key'), 'motifs', ['motif_key'], unique=True)

    # 3. motif_story_claims
    op.create_table(
        'motif_story_claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_key', sa.String(length=100), nullable=False),
        sa.Column('motif_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('DOCUMENTED', 'CONTEXTUAL', 'CONTESTED', 'UNKNOWN', name='motif_story_status_enum', create_type=False), nullable=False, server_default='DOCUMENTED'),
        sa.Column('claim_text_tr', sa.String(length=2000), nullable=True),
        sa.Column('claim_text_en', sa.String(length=2000), nullable=True),
        sa.Column('context_note', sa.String(length=1000), nullable=True),
        sa.Column('contest_note', sa.String(length=1000), nullable=True),
        sa.Column('uncertainty_note', sa.String(length=1000), nullable=True),
        sa.Column('knowledge_version', sa.String(length=50), nullable=False, server_default='motif-story-knowledge-v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['motif_id'], ['motifs.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('claim_key')
    )
    op.create_index(op.f('ix_motif_story_claims_claim_key'), 'motif_story_claims', ['claim_key'], unique=True)
    op.create_index(op.f('ix_motif_story_claims_motif_id'), 'motif_story_claims', ['motif_id'], unique=False)

    # 4. motif_story_claim_sources
    op.create_table(
        'motif_story_claim_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('locator', sa.String(length=255), nullable=True),
        sa.Column('source_note', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['claim_id'], ['motif_story_claims.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['curated_sources.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('claim_id', 'source_id', name='uq_claim_source')
    )
    op.create_index(op.f('ix_motif_story_claim_sources_claim_id'), 'motif_story_claim_sources', ['claim_id'], unique=False)
    op.create_index(op.f('ix_motif_story_claim_sources_source_id'), 'motif_story_claim_sources', ['source_id'], unique=False)

    # 5. motif_story_claim_themes
    op.create_table(
        'motif_story_claim_themes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('theme_key', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['claim_id'], ['motif_story_claims.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('claim_id', 'theme_key', name='uq_claim_theme')
    )
    op.create_index(op.f('ix_motif_story_claim_themes_claim_id'), 'motif_story_claim_themes', ['claim_id'], unique=False)

def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(op.f('ix_motif_story_claim_themes_claim_id'), table_name='motif_story_claim_themes')
    op.drop_table('motif_story_claim_themes')

    op.drop_index(op.f('ix_motif_story_claim_sources_source_id'), table_name='motif_story_claim_sources')
    op.drop_index(op.f('ix_motif_story_claim_sources_claim_id'), table_name='motif_story_claim_sources')
    op.drop_table('motif_story_claim_sources')

    op.drop_index(op.f('ix_motif_story_claims_motif_id'), table_name='motif_story_claims')
    op.drop_index(op.f('ix_motif_story_claims_claim_key'), table_name='motif_story_claims')
    op.drop_table('motif_story_claims')

    op.drop_index(op.f('ix_motifs_motif_key'), table_name='motifs')
    op.drop_table('motifs')

    op.drop_index(op.f('ix_curated_sources_source_key'), table_name='curated_sources')
    op.drop_table('curated_sources')

    motif_story_status_enum = postgresql.ENUM('DOCUMENTED', 'CONTEXTUAL', 'CONTESTED', 'UNKNOWN', name='motif_story_status_enum')
    motif_story_status_enum.drop(bind, checkfirst=True)

    source_type_enum = postgresql.ENUM('MUSEUM_OBJECT', 'MUSEUM_CATALOG', 'ACADEMIC_ARTICLE', 'ACADEMIC_BOOK', 'INSTITUTIONAL_PUBLICATION', 'ARCHIVE_RECORD', 'OTHER', name='source_type_enum')
    source_type_enum.drop(bind, checkfirst=True)
