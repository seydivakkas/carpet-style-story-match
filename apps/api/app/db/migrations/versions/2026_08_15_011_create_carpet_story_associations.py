"""create carpet story associations tables

Revision ID: 2026_08_15_011
Revises: 2026_08_15_010
Create Date: 2026-08-15 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_011"
down_revision: Union[str, None] = "2026_08_15_010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enum tipleri tek bir kez oluşturulur; tekrar kullanılan alanlar DDL üretmez.
    if op.get_bind().dialect.name == 'postgresql':
        postgresql.ENUM('CURATOR_CONFIRMED', 'SOURCE_DOCUMENTED', 'UNCERTAIN', name='motif_evidence_type_enum').create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()

    motif_evidence_type_enum = postgresql.ENUM(
        'CURATOR_CONFIRMED', 'SOURCE_DOCUMENTED', 'UNCERTAIN',
        name='motif_evidence_type_enum', create_type=False
    )
    motif_evidence_type_enum.create(bind, checkfirst=True)

    # 1. carpet_motif_associations
    op.create_table(
        'carpet_motif_associations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('carpet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('motif_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evidence_type', postgresql.ENUM('CURATOR_CONFIRMED', 'SOURCE_DOCUMENTED', 'UNCERTAIN', name='motif_evidence_type_enum', create_type=False), nullable=False, server_default='CURATOR_CONFIRMED'),
        sa.Column('curation_note', sa.String(length=1000), nullable=True),
        sa.Column('uncertainty_note', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['carpet_id'], ['carpets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['motif_id'], ['motifs.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('carpet_id', 'motif_id', name='uq_carpet_motif')
    )
    op.create_index(op.f('ix_carpet_motif_associations_carpet_id'), 'carpet_motif_associations', ['carpet_id'], unique=False)
    op.create_index(op.f('ix_carpet_motif_associations_motif_id'), 'carpet_motif_associations', ['motif_id'], unique=False)

    # 2. carpet_motif_association_sources
    op.create_table(
        'carpet_motif_association_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('association_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('locator', sa.String(length=255), nullable=True),
        sa.Column('source_note', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['association_id'], ['carpet_motif_associations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['curated_sources.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('association_id', 'source_id', name='uq_carpet_motif_source')
    )
    op.create_index(op.f('ix_carpet_motif_association_sources_association_id'), 'carpet_motif_association_sources', ['association_id'], unique=False)
    op.create_index(op.f('ix_carpet_motif_association_sources_source_id'), 'carpet_motif_association_sources', ['source_id'], unique=False)

    # 3. carpet_story_associations
    op.create_table(
        'carpet_story_associations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('carpet_motif_association_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('applicability_note', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['carpet_motif_association_id'], ['carpet_motif_associations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['claim_id'], ['motif_story_claims.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('carpet_motif_association_id', 'claim_id', name='uq_carpet_story_claim')
    )
    op.create_index(op.f('ix_carpet_story_associations_carpet_motif_association_id'), 'carpet_story_associations', ['carpet_motif_association_id'], unique=False)
    op.create_index(op.f('ix_carpet_story_associations_claim_id'), 'carpet_story_associations', ['claim_id'], unique=False)

def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(op.f('ix_carpet_story_associations_claim_id'), table_name='carpet_story_associations')
    op.drop_index(op.f('ix_carpet_story_associations_carpet_motif_association_id'), table_name='carpet_story_associations')
    op.drop_table('carpet_story_associations')

    op.drop_index(op.f('ix_carpet_motif_association_sources_source_id'), table_name='carpet_motif_association_sources')
    op.drop_index(op.f('ix_carpet_motif_association_sources_association_id'), table_name='carpet_motif_association_sources')
    op.drop_table('carpet_motif_association_sources')

    op.drop_index(op.f('ix_carpet_motif_associations_motif_id'), table_name='carpet_motif_associations')
    op.drop_index(op.f('ix_carpet_motif_associations_carpet_id'), table_name='carpet_motif_associations')
    op.drop_table('carpet_motif_associations')

    motif_evidence_type_enum = postgresql.ENUM('CURATOR_CONFIRMED', 'SOURCE_DOCUMENTED', 'UNCERTAIN', name='motif_evidence_type_enum')
    motif_evidence_type_enum.drop(bind, checkfirst=True)
