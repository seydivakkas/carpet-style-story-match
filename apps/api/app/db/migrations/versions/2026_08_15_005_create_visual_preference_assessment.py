"""create visual preference assessment tables and extend assessment status enum

Revision ID: 2026_08_15_005
Revises: 2026_08_15_004
Create Date: 2026-08-15 18:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_005"
down_revision: Union[str, None] = "2026_08_15_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enum tipleri tek bir kez oluşturulur; tekrar kullanılan alanlar DDL üretmez.
    if op.get_bind().dialect.name == 'postgresql':
        postgresql.ENUM('STRONGLY_LEFT', 'SLIGHTLY_LEFT', 'NEUTRAL', 'SLIGHTLY_RIGHT', 'STRONGLY_RIGHT', name='visual_choice_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('MEASURED', 'NOT_MEASURED', name='preference_dimension_status_enum').create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE assessment_status_enum ADD VALUE IF NOT EXISTS 'VISUAL_PENDING';")
        op.execute("ALTER TYPE assessment_status_enum ADD VALUE IF NOT EXISTS 'VISUAL_COMPLETE';")

    visual_choice_enum = postgresql.ENUM(
        'STRONGLY_LEFT', 'SLIGHTLY_LEFT', 'NEUTRAL', 'SLIGHTLY_RIGHT', 'STRONGLY_RIGHT',
        name='visual_choice_enum',
        create_type=False
    )
    visual_choice_enum.create(bind, checkfirst=True)

    # 1. visual_preference_presentations
    op.create_table(
        'visual_preference_presentations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stimulus_key', sa.String(length=50), nullable=False),
        sa.Column('stimulus_version', sa.String(length=50), nullable=False, server_default='visual-preference-stimuli-v1'),
        sa.Column('left_variant', sa.String(length=10), nullable=False),
        sa.Column('right_variant', sa.String(length=10), nullable=False),
        sa.Column('left_asset_sha256', sa.String(length=64), nullable=False),
        sa.Column('right_asset_sha256', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'stimulus_key', name='uq_assessment_stimulus_presentation')
    )
    op.create_index(op.f('ix_visual_preference_presentations_assessment_id'), 'visual_preference_presentations', ['assessment_id'], unique=False)

    # 2. visual_preference_responses
    op.create_table(
        'visual_preference_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stimulus_key', sa.String(length=50), nullable=False),
        sa.Column(
            'choice',
            postgresql.ENUM('STRONGLY_LEFT', 'SLIGHTLY_LEFT', 'NEUTRAL', 'SLIGHTLY_RIGHT', 'STRONGLY_RIGHT', name='visual_choice_enum', create_type=False),
            nullable=False
        ),
        sa.Column('canonical_direction', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'stimulus_key', name='uq_assessment_stimulus_response')
    )
    op.create_index(op.f('ix_visual_preference_responses_assessment_id'), 'visual_preference_responses', ['assessment_id'], unique=False)

    # 3. visual_preference_profiles
    op.create_table(
        'visual_preference_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evidence_version', sa.String(length=50), nullable=False, server_default='visual-preference-evidence-v1'),
        sa.Column('stimulus_version', sa.String(length=50), nullable=False, server_default='visual-preference-stimuli-v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', name='uq_visual_profile_assessment_id')
    )
    op.create_index(op.f('ix_visual_preference_profiles_assessment_id'), 'visual_preference_profiles', ['assessment_id'], unique=True)

    # 4. visual_preference_dimensions
    op.create_table(
        'visual_preference_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dimension_key', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM('MEASURED', 'NOT_MEASURED', name='preference_dimension_status_enum', create_type=False),
            nullable=False,
            server_default='MEASURED'
        ),
        sa.Column('evidence_weight', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['profile_id'], ['visual_preference_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_id', 'dimension_key', name='uq_visual_profile_dimension_key')
    )
    op.create_index(op.f('ix_visual_preference_dimensions_profile_id'), 'visual_preference_dimensions', ['profile_id'], unique=False)

def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index(op.f('ix_visual_preference_dimensions_profile_id'), table_name='visual_preference_dimensions')
    op.drop_table('visual_preference_dimensions')

    op.drop_index(op.f('ix_visual_preference_profiles_assessment_id'), table_name='visual_preference_profiles')
    op.drop_table('visual_preference_profiles')

    op.drop_index(op.f('ix_visual_preference_responses_assessment_id'), table_name='visual_preference_responses')
    op.drop_table('visual_preference_responses')

    op.drop_index(op.f('ix_visual_preference_presentations_assessment_id'), table_name='visual_preference_presentations')
    op.drop_table('visual_preference_presentations')

    visual_choice_enum = postgresql.ENUM(
        'STRONGLY_LEFT', 'SLIGHTLY_LEFT', 'NEUTRAL', 'SLIGHTLY_RIGHT', 'STRONGLY_RIGHT',
        name='visual_choice_enum'
    )
    visual_choice_enum.drop(bind, checkfirst=True)
