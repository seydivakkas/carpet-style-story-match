"""create narrative affinity tables

Revision ID: 2026_08_15_012
Revises: 2026_08_15_011
Create Date: 2026-08-15 23:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_012"
down_revision: Union[str, None] = "2026_08_15_011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum tipleri tek bir kez oluşturulur; tekrar kullanılan alanlar DDL üretmez.
    if op.get_bind().dialect.name == 'postgresql':
        postgresql.ENUM('AVAILABLE', 'NOT_AVAILABLE', name='narrative_affinity_status_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('USER_NARRATIVE_SKIPPED', 'NO_SELECTED_USER_THEMES', 'NO_CARPET_NARRATIVE_THEME_EVIDENCE', 'ONLY_CONTESTED_CARPET_EVIDENCE', name='narrative_not_available_reason_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('VERY_STRONG', 'STRONG', 'MODERATE', 'LIMITED', name='narrative_affinity_level_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('PRIMARY', 'SECONDARY', 'NOT_SELECTED', name='narrative_interest_level_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('DOCUMENTED', 'CONTEXTUAL', 'CONTESTED_ONLY', 'NO_EVIDENCE', name='theme_support_status_enum').create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()

    narrative_affinity_status_enum = postgresql.ENUM(
        'AVAILABLE', 'NOT_AVAILABLE',
        name='narrative_affinity_status_enum', create_type=False
    )
    narrative_affinity_status_enum.create(bind, checkfirst=True)

    narrative_affinity_level_enum = postgresql.ENUM(
        'VERY_STRONG', 'STRONG', 'MODERATE', 'LIMITED',
        name='narrative_affinity_level_enum', create_type=False
    )
    narrative_affinity_level_enum.create(bind, checkfirst=True)

    narrative_not_available_reason_enum = postgresql.ENUM(
        'USER_NARRATIVE_SKIPPED', 'NO_SELECTED_USER_THEMES',
        'NO_CARPET_NARRATIVE_THEME_EVIDENCE', 'ONLY_CONTESTED_CARPET_EVIDENCE',
        name='narrative_not_available_reason_enum', create_type=False
    )
    narrative_not_available_reason_enum.create(bind, checkfirst=True)

    theme_support_status_enum = postgresql.ENUM(
        'DOCUMENTED', 'CONTEXTUAL', 'CONTESTED_ONLY', 'NO_EVIDENCE',
        name='theme_support_status_enum', create_type=False
    )
    theme_support_status_enum.create(bind, checkfirst=True)

    # 1. narrative_affinity_results
    op.create_table(
        'narrative_affinity_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_narrative_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('carpet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('affinity_version', sa.String(length=50), nullable=False),
        sa.Column('carpet_narrative_snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('status', postgresql.ENUM('AVAILABLE', 'NOT_AVAILABLE', name='narrative_affinity_status_enum', create_type=False), nullable=False),
        sa.Column('not_available_reason', postgresql.ENUM('USER_NARRATIVE_SKIPPED', 'NO_SELECTED_USER_THEMES', 'NO_CARPET_NARRATIVE_THEME_EVIDENCE', 'ONLY_CONTESTED_CARPET_EVIDENCE', name='narrative_not_available_reason_enum', create_type=False), nullable=True),
        sa.Column('affinity_level', postgresql.ENUM('VERY_STRONG', 'STRONG', 'MODERATE', 'LIMITED', name='narrative_affinity_level_enum', create_type=False), nullable=True),
        sa.Column('confirmed_interest_coverage', sa.Float(), nullable=True),
        sa.Column('selected_theme_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('selected_interest_weight', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('confirmed_matched_theme_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('confirmed_matched_interest_weight', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('contested_overlap_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['carpet_id'], ['carpets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_narrative_profile_id'], ['user_narrative_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_narrative_profile_id',
            'carpet_id',
            'carpet_narrative_snapshot_hash',
            'affinity_version',
            name='uq_narrative_affinity_snapshot'
        )
    )
    op.create_index(op.f('ix_narrative_affinity_results_assessment_id'), 'narrative_affinity_results', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_narrative_affinity_results_carpet_id'), 'narrative_affinity_results', ['carpet_id'], unique=False)
    op.create_index(op.f('ix_narrative_affinity_results_user_narrative_profile_id'), 'narrative_affinity_results', ['user_narrative_profile_id'], unique=False)

    # 2. narrative_affinity_theme_results
    op.create_table(
        'narrative_affinity_theme_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('affinity_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('theme_key', sa.String(length=50), nullable=False),
        sa.Column('user_interest_level', postgresql.ENUM('PRIMARY', 'SECONDARY', 'NOT_SELECTED', name='narrative_interest_level_enum', create_type=False), nullable=False),
        sa.Column('user_interest_weight', sa.Float(), nullable=False),
        sa.Column('user_selected', sa.Boolean(), nullable=False),
        sa.Column('carpet_support_status', postgresql.ENUM('DOCUMENTED', 'CONTEXTUAL', 'CONTESTED_ONLY', 'NO_EVIDENCE', name='theme_support_status_enum', create_type=False), nullable=False),
        sa.Column('confirmed_match', sa.Boolean(), nullable=False),
        sa.Column('contested_overlap', sa.Boolean(), nullable=False),
        sa.Column('has_contested_evidence', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['affinity_result_id'], ['narrative_affinity_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('affinity_result_id', 'theme_key', name='uq_narrative_affinity_theme')
    )
    op.create_index(op.f('ix_narrative_affinity_theme_results_affinity_result_id'), 'narrative_affinity_theme_results', ['affinity_result_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(op.f('ix_narrative_affinity_theme_results_affinity_result_id'), table_name='narrative_affinity_theme_results')
    op.drop_table('narrative_affinity_theme_results')

    op.drop_index(op.f('ix_narrative_affinity_results_user_narrative_profile_id'), table_name='narrative_affinity_results')
    op.drop_index(op.f('ix_narrative_affinity_results_carpet_id'), table_name='narrative_affinity_results')
    op.drop_index(op.f('ix_narrative_affinity_results_assessment_id'), table_name='narrative_affinity_results')
    op.drop_table('narrative_affinity_results')

    theme_support_status_enum = postgresql.ENUM('DOCUMENTED', 'CONTEXTUAL', 'CONTESTED_ONLY', 'NO_EVIDENCE', name='theme_support_status_enum')
    theme_support_status_enum.drop(bind, checkfirst=True)

    narrative_not_available_reason_enum = postgresql.ENUM('USER_NARRATIVE_SKIPPED', 'NO_SELECTED_USER_THEMES', 'NO_CARPET_NARRATIVE_THEME_EVIDENCE', 'ONLY_CONTESTED_CARPET_EVIDENCE', name='narrative_not_available_reason_enum')
    narrative_not_available_reason_enum.drop(bind, checkfirst=True)

    narrative_affinity_level_enum = postgresql.ENUM('VERY_STRONG', 'STRONG', 'MODERATE', 'LIMITED', name='narrative_affinity_level_enum')
    narrative_affinity_level_enum.drop(bind, checkfirst=True)

    narrative_affinity_status_enum = postgresql.ENUM('AVAILABLE', 'NOT_AVAILABLE', name='narrative_affinity_status_enum')
    narrative_affinity_status_enum.drop(bind, checkfirst=True)
