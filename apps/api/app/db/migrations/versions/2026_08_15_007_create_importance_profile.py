"""create importance profile tables

Revision ID: 2026_08_15_007
Revises: 2026_08_15_006
Create Date: 2026-08-15 19:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_007"
down_revision: Union[str, None] = "2026_08_15_006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enum tipleri tek bir kez oluşturulur; tekrar kullanılan alanlar DDL üretmez.
    if op.get_bind().dialect.name == 'postgresql':
        postgresql.ENUM('EXPLICIT_SELECTION', 'SKIPPED_ALL_STANDARD', name='importance_completion_mode_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('PRIORITY', 'STANDARD', 'FLEXIBLE', name='importance_level_enum').create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE assessment_status_enum ADD VALUE IF NOT EXISTS 'IMPORTANCE_COMPLETE';")

    importance_level_enum = postgresql.ENUM('PRIORITY', 'STANDARD', 'FLEXIBLE', name='importance_level_enum', create_type=False)
    importance_level_enum.create(bind, checkfirst=True)

    importance_completion_mode_enum = postgresql.ENUM('EXPLICIT_SELECTION', 'SKIPPED_ALL_STANDARD', name='importance_completion_mode_enum', create_type=False)
    importance_completion_mode_enum.create(bind, checkfirst=True)

    # 1. importance_profiles
    op.create_table(
        'importance_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_preference_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('importance_version', sa.String(length=50), nullable=False, server_default='importance-v1'),
        sa.Column('completion_mode', postgresql.ENUM('EXPLICIT_SELECTION', 'SKIPPED_ALL_STANDARD', name='importance_completion_mode_enum', create_type=False), nullable=False, server_default='EXPLICIT_SELECTION'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_preference_profile_id'], ['user_preference_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'importance_version', name='uq_importance_profile_assessment_version')
    )
    op.create_index(op.f('ix_importance_profiles_assessment_id'), 'importance_profiles', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_importance_profiles_user_preference_profile_id'), 'importance_profiles', ['user_preference_profile_id'], unique=False)

    # 2. importance_dimensions
    op.create_table(
        'importance_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('importance_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dimension_key', sa.String(length=50), nullable=False),
        sa.Column('level', postgresql.ENUM('PRIORITY', 'STANDARD', 'FLEXIBLE', name='importance_level_enum', create_type=False), nullable=False, server_default='STANDARD'),
        sa.Column('weight', sa.Float(), nullable=False, server_default='0.60'),
        sa.ForeignKeyConstraint(['importance_profile_id'], ['importance_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('importance_profile_id', 'dimension_key', name='uq_importance_dimension_key')
    )
    op.create_index(op.f('ix_importance_dimensions_importance_profile_id'), 'importance_dimensions', ['importance_profile_id'], unique=False)

def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index(op.f('ix_importance_dimensions_importance_profile_id'), table_name='importance_dimensions')
    op.drop_table('importance_dimensions')

    op.drop_index(op.f('ix_importance_profiles_user_preference_profile_id'), table_name='importance_profiles')
    op.drop_index(op.f('ix_importance_profiles_assessment_id'), table_name='importance_profiles')
    op.drop_table('importance_profiles')

    importance_completion_mode_enum = postgresql.ENUM('EXPLICIT_SELECTION', 'SKIPPED_ALL_STANDARD', name='importance_completion_mode_enum')
    importance_completion_mode_enum.drop(bind, checkfirst=True)

    importance_level_enum = postgresql.ENUM('PRIORITY', 'STANDARD', 'FLEXIBLE', name='importance_level_enum')
    importance_level_enum.drop(bind, checkfirst=True)
