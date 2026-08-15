"""create historical connection tables

Revision ID: 2026_08_15_014
Revises: 2026_08_15_013
Create Date: 2026-08-15 23:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_014"
down_revision: Union[str, None] = "2026_08_15_013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    historical_connection_status_enum = postgresql.ENUM(
        'COMPLETE', 'PARTIAL', 'NOT_AVAILABLE',
        name='historical_connection_status_enum', create_type=False
    )
    historical_connection_status_enum.create(bind, checkfirst=True)

    historical_connection_not_available_reason_enum = postgresql.ENUM(
        'INSUFFICIENT_COMPARABLE_DIMENSIONS',
        name='historical_connection_not_available_reason_enum', create_type=False
    )
    historical_connection_not_available_reason_enum.create(bind, checkfirst=True)

    historical_connection_level_enum = postgresql.ENUM(
        'VERY_CLOSE', 'CLOSE', 'MODERATE', 'LIMITED',
        name='historical_connection_level_enum', create_type=False
    )
    historical_connection_level_enum.create(bind, checkfirst=True)

    # 1. historical_connection_results
    op.create_table(
        'historical_connection_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_carpet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_style_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('historical_carpet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('historical_reference_metadata_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('historical_style_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connection_version', sa.String(length=50), nullable=False, server_default='historical-connection-v1'),
        sa.Column('status', sa.Enum('COMPLETE', 'PARTIAL', 'NOT_AVAILABLE', name='historical_connection_status_enum'), nullable=False),
        sa.Column('not_available_reason', sa.Enum('INSUFFICIENT_COMPARABLE_DIMENSIONS', name='historical_connection_not_available_reason_enum'), nullable=True),
        sa.Column('style_similarity', sa.Float(), nullable=True),
        sa.Column('connection_level', sa.Enum('VERY_CLOSE', 'CLOSE', 'MODERATE', 'LIMITED', name='historical_connection_level_enum'), nullable=True),
        sa.Column('comparable_dimension_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('dimension_coverage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint('style_similarity IS NULL OR (style_similarity >= 0.0 AND style_similarity <= 1.0)', name='check_hist_conn_similarity_range'),
        sa.CheckConstraint('dimension_coverage >= 0.0 AND dimension_coverage <= 1.0', name='check_hist_conn_coverage_range'),
        sa.ForeignKeyConstraint(['historical_carpet_id'], ['carpets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['historical_reference_metadata_id'], ['historical_reference_metadata.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['historical_style_profile_id'], ['carpet_style_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_carpet_id'], ['carpets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_style_profile_id'], ['carpet_style_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('target_style_profile_id', 'historical_style_profile_id', 'connection_version', name='uq_historical_connection_profiles')
    )
    op.create_index(op.f('ix_historical_connection_results_target_carpet_id'), 'historical_connection_results', ['target_carpet_id'], unique=False)
    op.create_index(op.f('ix_historical_connection_results_target_style_profile_id'), 'historical_connection_results', ['target_style_profile_id'], unique=False)
    op.create_index(op.f('ix_historical_connection_results_historical_carpet_id'), 'historical_connection_results', ['historical_carpet_id'], unique=False)
    op.create_index(op.f('ix_historical_connection_results_historical_reference_metadata_id'), 'historical_connection_results', ['historical_reference_metadata_id'], unique=False)
    op.create_index(op.f('ix_historical_connection_results_historical_style_profile_id'), 'historical_connection_results', ['historical_style_profile_id'], unique=False)

    # 2. historical_connection_dimensions
    op.create_table(
        'historical_connection_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('historical_connection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dimension_key', sa.String(length=50), nullable=False),
        sa.Column('target_value', sa.Float(), nullable=True),
        sa.Column('target_status', sa.String(length=50), nullable=False),
        sa.Column('target_confidence', sa.Float(), nullable=True),
        sa.Column('reference_value', sa.Float(), nullable=True),
        sa.Column('reference_status', sa.String(length=50), nullable=False),
        sa.Column('reference_confidence', sa.Float(), nullable=True),
        sa.Column('difference', sa.Float(), nullable=True),
        sa.Column('similarity', sa.Float(), nullable=True),
        sa.Column('comparable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint('difference IS NULL OR (difference >= 0.0 AND difference <= 1.0)', name='check_hist_conn_dim_diff_range'),
        sa.CheckConstraint('similarity IS NULL OR (similarity >= 0.0 AND similarity <= 1.0)', name='check_hist_conn_dim_sim_range'),
        sa.ForeignKeyConstraint(['historical_connection_id'], ['historical_connection_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('historical_connection_id', 'dimension_key', name='uq_historical_connection_dimension')
    )
    op.create_index(op.f('ix_historical_connection_dimensions_historical_connection_id'), 'historical_connection_dimensions', ['historical_connection_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(op.f('ix_historical_connection_dimensions_historical_connection_id'), table_name='historical_connection_dimensions')
    op.drop_table('historical_connection_dimensions')

    op.drop_index(op.f('ix_historical_connection_results_historical_style_profile_id'), table_name='historical_connection_results')
    op.drop_index(op.f('ix_historical_connection_results_historical_reference_metadata_id'), table_name='historical_connection_results')
    op.drop_index(op.f('ix_historical_connection_results_historical_carpet_id'), table_name='historical_connection_results')
    op.drop_index(op.f('ix_historical_connection_results_target_style_profile_id'), table_name='historical_connection_results')
    op.drop_index(op.f('ix_historical_connection_results_target_carpet_id'), table_name='historical_connection_results')
    op.drop_table('historical_connection_results')

    historical_connection_level_enum = postgresql.ENUM('VERY_CLOSE', 'CLOSE', 'MODERATE', 'LIMITED', name='historical_connection_level_enum')
    historical_connection_level_enum.drop(bind, checkfirst=True)

    historical_connection_not_available_reason_enum = postgresql.ENUM('INSUFFICIENT_COMPARABLE_DIMENSIONS', name='historical_connection_not_available_reason_enum')
    historical_connection_not_available_reason_enum.drop(bind, checkfirst=True)

    historical_connection_status_enum = postgresql.ENUM('COMPLETE', 'PARTIAL', 'NOT_AVAILABLE', name='historical_connection_status_enum')
    historical_connection_status_enum.drop(bind, checkfirst=True)
