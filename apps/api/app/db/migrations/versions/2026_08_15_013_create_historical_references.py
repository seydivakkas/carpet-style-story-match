"""create historical reference tables

Revision ID: 2026_08_15_013
Revises: 2026_08_15_012
Create Date: 2026-08-15 23:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_013"
down_revision: Union[str, None] = "2026_08_15_012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    historical_source_role_enum = postgresql.ENUM(
        'PRIMARY_OBJECT_RECORD', 'SUPPORTING_REFERENCE',
        name='historical_source_role_enum', create_type=False
    )
    historical_source_role_enum.create(bind, checkfirst=True)

    # 1. historical_reference_metadata
    op.create_table(
        'historical_reference_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('carpet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reference_key', sa.String(length=100), nullable=False),
        sa.Column('institution_name', sa.String(length=255), nullable=False),
        sa.Column('object_identifier', sa.String(length=255), nullable=False),
        sa.Column('accession_number', sa.String(length=255), nullable=True),
        sa.Column('object_title', sa.String(length=500), nullable=False),
        sa.Column('culture', sa.String(length=255), nullable=True),
        sa.Column('period', sa.String(length=255), nullable=True),
        sa.Column('dynasty_or_tradition', sa.String(length=255), nullable=True),
        sa.Column('date_display', sa.String(length=255), nullable=True),
        sa.Column('date_start_year', sa.Integer(), nullable=True),
        sa.Column('date_end_year', sa.Integer(), nullable=True),
        sa.Column('geography', sa.String(length=255), nullable=True),
        sa.Column('medium', sa.String(length=255), nullable=True),
        sa.Column('dimensions_text', sa.String(length=255), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('credit_line', sa.Text(), nullable=True),
        sa.Column('object_url', sa.Text(), nullable=True),
        sa.Column('source_image_url', sa.Text(), nullable=True),
        sa.Column('rights_statement', sa.Text(), nullable=True),
        sa.Column('open_access', sa.Boolean(), nullable=True),
        sa.Column('curation_note', sa.Text(), nullable=True),
        sa.Column('schema_version', sa.String(length=50), nullable=False, server_default='historical-reference-curation-v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['carpet_id'], ['carpets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('carpet_id', name='uq_historical_ref_carpet_id'),
        sa.UniqueConstraint('reference_key', name='uq_historical_ref_reference_key'),
        sa.UniqueConstraint('institution_name', 'object_identifier', name='uq_historical_ref_institution_object_id')
    )
    op.create_index(op.f('ix_historical_reference_metadata_carpet_id'), 'historical_reference_metadata', ['carpet_id'], unique=True)
    op.create_index(op.f('ix_historical_reference_metadata_reference_key'), 'historical_reference_metadata', ['reference_key'], unique=True)
    op.create_index(op.f('ix_historical_reference_metadata_institution_name'), 'historical_reference_metadata', ['institution_name'], unique=False)
    op.create_index(op.f('ix_historical_reference_metadata_object_identifier'), 'historical_reference_metadata', ['object_identifier'], unique=False)
    op.create_index(op.f('ix_historical_reference_metadata_culture'), 'historical_reference_metadata', ['culture'], unique=False)
    op.create_index(op.f('ix_historical_reference_metadata_period'), 'historical_reference_metadata', ['period'], unique=False)
    op.create_index(op.f('ix_historical_reference_metadata_dynasty_or_tradition'), 'historical_reference_metadata', ['dynasty_or_tradition'], unique=False)
    op.create_index(op.f('ix_historical_reference_metadata_department'), 'historical_reference_metadata', ['department'], unique=False)

    # 2. historical_reference_sources
    op.create_table(
        'historical_reference_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('historical_reference_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_role', sa.Enum('PRIMARY_OBJECT_RECORD', 'SUPPORTING_REFERENCE', name='historical_source_role_enum'), nullable=False),
        sa.Column('locator', sa.String(length=255), nullable=True),
        sa.Column('source_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['historical_reference_id'], ['historical_reference_metadata.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['curated_sources.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('historical_reference_id', 'source_id', name='uq_historical_ref_source')
    )
    op.create_index(op.f('ix_historical_reference_sources_historical_reference_id'), 'historical_reference_sources', ['historical_reference_id'], unique=False)
    op.create_index(op.f('ix_historical_reference_sources_source_id'), 'historical_reference_sources', ['source_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(op.f('ix_historical_reference_sources_source_id'), table_name='historical_reference_sources')
    op.drop_index(op.f('ix_historical_reference_sources_historical_reference_id'), table_name='historical_reference_sources')
    op.drop_table('historical_reference_sources')

    op.drop_index(op.f('ix_historical_reference_metadata_department'), table_name='historical_reference_metadata')
    op.drop_index(op.f('ix_historical_reference_metadata_dynasty_or_tradition'), table_name='historical_reference_metadata')
    op.drop_index(op.f('ix_historical_reference_metadata_period'), table_name='historical_reference_metadata')
    op.drop_index(op.f('ix_historical_reference_metadata_culture'), table_name='historical_reference_metadata')
    op.drop_index(op.f('ix_historical_reference_metadata_object_identifier'), table_name='historical_reference_metadata')
    op.drop_index(op.f('ix_historical_reference_metadata_institution_name'), table_name='historical_reference_metadata')
    op.drop_index(op.f('ix_historical_reference_metadata_reference_key'), table_name='historical_reference_metadata')
    op.drop_index(op.f('ix_historical_reference_metadata_carpet_id'), table_name='historical_reference_metadata')
    op.drop_table('historical_reference_metadata')

    historical_source_role_enum = postgresql.ENUM('PRIMARY_OBJECT_RECORD', 'SUPPORTING_REFERENCE', name='historical_source_role_enum')
    historical_source_role_enum.drop(bind, checkfirst=True)
