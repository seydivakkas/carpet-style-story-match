"""create visual style match tables

Revision ID: 2026_08_15_008
Revises: 2026_08_15_007
Create Date: 2026-08-15 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_008"
down_revision: Union[str, None] = "2026_08_15_007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enum tipleri tek bir kez oluşturulur; tekrar kullanılan alanlar DDL üretmez.
    if op.get_bind().dialect.name == 'postgresql':
        postgresql.ENUM('COMPLETE', 'PARTIAL', 'NOT_AVAILABLE', name='style_match_status_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('VERY_STRONG', 'STRONG', 'MODERATE', 'LIMITED', 'LOW', name='style_match_label_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('INFERRED', 'USER_CONFIRMED', 'USER_OVERRIDDEN', name='user_preference_provenance_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('PRIORITY', 'STANDARD', 'FLEXIBLE', name='importance_level_enum').create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()

    style_match_status_enum = postgresql.ENUM('COMPLETE', 'PARTIAL', 'NOT_AVAILABLE', name='style_match_status_enum', create_type=False)
    style_match_status_enum.create(bind, checkfirst=True)

    style_match_label_enum = postgresql.ENUM('VERY_STRONG', 'STRONG', 'MODERATE', 'LIMITED', 'LOW', name='style_match_label_enum', create_type=False)
    style_match_label_enum.create(bind, checkfirst=True)

    importance_level_enum = postgresql.ENUM('PRIORITY', 'STANDARD', 'FLEXIBLE', name='importance_level_enum', create_type=False)
    importance_level_enum.create(bind, checkfirst=True)

    user_provenance_enum = postgresql.ENUM('INFERRED', 'USER_CONFIRMED', 'USER_OVERRIDDEN', name='user_preference_provenance_enum', create_type=False)
    user_provenance_enum.create(bind, checkfirst=True)

    # 1. visual_style_match_results
    op.create_table(
        'visual_style_match_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_preference_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('importance_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('carpet_style_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('match_version', sa.String(length=50), nullable=False, server_default='visual-style-match-v1'),
        sa.Column('status', postgresql.ENUM('COMPLETE', 'PARTIAL', 'NOT_AVAILABLE', name='style_match_status_enum', create_type=False), nullable=False, server_default='COMPLETE'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('score_100', sa.Float(), nullable=True),
        sa.Column('match_label', postgresql.ENUM('VERY_STRONG', 'STRONG', 'MODERATE', 'LIMITED', 'LOW', name='style_match_label_enum', create_type=False), nullable=True),
        sa.Column('comparable_dimension_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('weighted_coverage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_importance_weight', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('comparable_weight', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('explanation_json', sa.String(length=2000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_preference_profile_id'], ['user_preference_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['importance_profile_id'], ['importance_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['carpet_style_profile_id'], ['carpet_style_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'user_preference_profile_id', 'importance_profile_id', 'carpet_style_profile_id', 'match_version', name='uq_style_match_assessment_profiles')
    )
    op.create_index(op.f('ix_visual_style_match_results_assessment_id'), 'visual_style_match_results', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_visual_style_match_results_user_preference_profile_id'), 'visual_style_match_results', ['user_preference_profile_id'], unique=False)
    op.create_index(op.f('ix_visual_style_match_results_importance_profile_id'), 'visual_style_match_results', ['importance_profile_id'], unique=False)
    op.create_index(op.f('ix_visual_style_match_results_carpet_style_profile_id'), 'visual_style_match_results', ['carpet_style_profile_id'], unique=False)

    # 2. visual_style_match_dimensions
    op.create_table(
        'visual_style_match_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('match_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dimension_key', sa.String(length=50), nullable=False),
        sa.Column('user_value', sa.Float(), nullable=True),
        sa.Column('user_provenance', postgresql.ENUM('INFERRED', 'USER_CONFIRMED', 'USER_OVERRIDDEN', name='user_preference_provenance_enum', create_type=False), nullable=True),
        sa.Column('carpet_value', sa.Float(), nullable=True),
        sa.Column('carpet_dimension_status', sa.String(length=50), nullable=True),
        sa.Column('importance_level', postgresql.ENUM('PRIORITY', 'STANDARD', 'FLEXIBLE', name='importance_level_enum', create_type=False), nullable=False, server_default='STANDARD'),
        sa.Column('importance_weight', sa.Float(), nullable=False, server_default='0.60'),
        sa.Column('difference', sa.Float(), nullable=True),
        sa.Column('similarity', sa.Float(), nullable=True),
        sa.Column('weighted_similarity', sa.Float(), nullable=True),
        sa.Column('weighted_difference', sa.Float(), nullable=True),
        sa.Column('comparable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('user_preference_confidence', sa.Float(), nullable=True),
        sa.Column('carpet_measurement_confidence', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['match_result_id'], ['visual_style_match_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_result_id', 'dimension_key', name='uq_match_dimension_key')
    )
    op.create_index(op.f('ix_visual_style_match_dimensions_match_result_id'), 'visual_style_match_dimensions', ['match_result_id'], unique=False)

def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index(op.f('ix_visual_style_match_dimensions_match_result_id'), table_name='visual_style_match_dimensions')
    op.drop_table('visual_style_match_dimensions')

    op.drop_index(op.f('ix_visual_style_match_results_carpet_style_profile_id'), table_name='visual_style_match_results')
    op.drop_index(op.f('ix_visual_style_match_results_importance_profile_id'), table_name='visual_style_match_results')
    op.drop_index(op.f('ix_visual_style_match_results_user_preference_profile_id'), table_name='visual_style_match_results')
    op.drop_index(op.f('ix_visual_style_match_results_assessment_id'), table_name='visual_style_match_results')
    op.drop_table('visual_style_match_results')

    style_match_label_enum = postgresql.ENUM('VERY_STRONG', 'STRONG', 'MODERATE', 'LIMITED', 'LOW', name='style_match_label_enum')
    style_match_label_enum.drop(bind, checkfirst=True)

    style_match_status_enum = postgresql.ENUM('COMPLETE', 'PARTIAL', 'NOT_AVAILABLE', name='style_match_status_enum')
    style_match_status_enum.drop(bind, checkfirst=True)
