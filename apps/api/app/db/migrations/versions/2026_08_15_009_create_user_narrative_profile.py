"""create user narrative profile tables

Revision ID: 2026_08_15_009
Revises: 2026_08_15_008
Create Date: 2026-08-15 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_009"
down_revision: Union[str, None] = "2026_08_15_008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enum tipleri tek bir kez oluşturulur; tekrar kullanılan alanlar DDL üretmez.
    if op.get_bind().dialect.name == 'postgresql':
        postgresql.ENUM('EXPLICIT_SELECTION', 'SKIPPED', name='narrative_completion_mode_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('PRIMARY', 'SECONDARY', 'NOT_SELECTED', name='narrative_interest_level_enum').create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()

    narrative_interest_level_enum = postgresql.ENUM('PRIMARY', 'SECONDARY', 'NOT_SELECTED', name='narrative_interest_level_enum', create_type=False)
    narrative_interest_level_enum.create(bind, checkfirst=True)

    narrative_completion_mode_enum = postgresql.ENUM('EXPLICIT_SELECTION', 'SKIPPED', name='narrative_completion_mode_enum', create_type=False)
    narrative_completion_mode_enum.create(bind, checkfirst=True)

    # 1. user_narrative_profiles
    op.create_table(
        'user_narrative_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_preference_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_version', sa.String(length=50), nullable=False, server_default='user-narrative-profile-v1'),
        sa.Column('completion_mode', postgresql.ENUM('EXPLICIT_SELECTION', 'SKIPPED', name='narrative_completion_mode_enum', create_type=False), nullable=False, server_default='EXPLICIT_SELECTION'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_preference_profile_id'], ['user_preference_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'profile_version', name='uq_narrative_profile_assessment_version')
    )
    op.create_index(op.f('ix_user_narrative_profiles_assessment_id'), 'user_narrative_profiles', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_user_narrative_profiles_user_preference_profile_id'), 'user_narrative_profiles', ['user_preference_profile_id'], unique=False)

    # 2. user_narrative_themes
    op.create_table(
        'user_narrative_themes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('narrative_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('theme_key', sa.String(length=50), nullable=False),
        sa.Column('interest_level', postgresql.ENUM('PRIMARY', 'SECONDARY', 'NOT_SELECTED', name='narrative_interest_level_enum', create_type=False), nullable=False, server_default='NOT_SELECTED'),
        sa.Column('interest_weight', sa.Float(), nullable=False, server_default='0.00'),
        sa.ForeignKeyConstraint(['narrative_profile_id'], ['user_narrative_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('narrative_profile_id', 'theme_key', name='uq_narrative_theme_key')
    )
    op.create_index(op.f('ix_user_narrative_themes_narrative_profile_id'), 'user_narrative_themes', ['narrative_profile_id'], unique=False)

def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index(op.f('ix_user_narrative_themes_narrative_profile_id'), table_name='user_narrative_themes')
    op.drop_table('user_narrative_themes')

    op.drop_index(op.f('ix_user_narrative_profiles_user_preference_profile_id'), table_name='user_narrative_profiles')
    op.drop_index(op.f('ix_user_narrative_profiles_assessment_id'), table_name='user_narrative_profiles')
    op.drop_table('user_narrative_profiles')

    narrative_completion_mode_enum = postgresql.ENUM('EXPLICIT_SELECTION', 'SKIPPED', name='narrative_completion_mode_enum')
    narrative_completion_mode_enum.drop(bind, checkfirst=True)

    narrative_interest_level_enum = postgresql.ENUM('PRIMARY', 'SECONDARY', 'NOT_SELECTED', name='narrative_interest_level_enum')
    narrative_interest_level_enum.drop(bind, checkfirst=True)
