"""create preference_assessments and text_preference_responses/profiles tables

Revision ID: 2026_08_15_004
Revises: 2026_08_15_003
Create Date: 2026-08-15 18:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_004"
down_revision: Union[str, None] = "2026_08_15_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    assessment_status_enum = postgresql.ENUM(
        'TEXT_PENDING', 'TEXT_COMPLETE',
        name='assessment_status_enum',
        create_type=False
    )
    assessment_status_enum.create(op.get_bind(), checkfirst=True)

    preference_dimension_status_enum = postgresql.ENUM(
        'MEASURED', 'NOT_MEASURED',
        name='preference_dimension_status_enum',
        create_type=False
    )
    preference_dimension_status_enum.create(op.get_bind(), checkfirst=True)

    text_choice_enum = postgresql.ENUM(
        'STRONGLY_A', 'SLIGHTLY_A', 'NEUTRAL', 'SLIGHTLY_B', 'STRONGLY_B',
        name='text_choice_enum',
        create_type=False
    )
    text_choice_enum.create(op.get_bind(), checkfirst=True)

    # 1. preference_assessments
    op.create_table(
        'preference_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'status',
            sa.Enum('TEXT_PENDING', 'TEXT_COMPLETE', name='assessment_status_enum'),
            nullable=False,
            server_default='TEXT_PENDING'
        ),
        sa.Column('evidence_version', sa.String(length=50), nullable=False, server_default='text-preference-evidence-v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. text_preference_responses
    op.create_table(
        'text_preference_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_key', sa.String(length=50), nullable=False),
        sa.Column(
            'choice',
            sa.Enum('STRONGLY_A', 'SLIGHTLY_A', 'NEUTRAL', 'SLIGHTLY_B', 'STRONGLY_B', name='text_choice_enum'),
            nullable=False
        ),
        sa.Column('response_value', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'question_key', name='uq_assessment_question_key')
    )
    op.create_index(op.f('ix_text_preference_responses_assessment_id'), 'text_preference_responses', ['assessment_id'], unique=False)

    # 3. text_preference_profiles
    op.create_table(
        'text_preference_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evidence_version', sa.String(length=50), nullable=False, server_default='text-preference-evidence-v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', name='uq_text_profile_assessment_id')
    )
    op.create_index(op.f('ix_text_preference_profiles_assessment_id'), 'text_preference_profiles', ['assessment_id'], unique=True)

    # 4. text_preference_dimensions
    op.create_table(
        'text_preference_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dimension_key', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('MEASURED', 'NOT_MEASURED', name='preference_dimension_status_enum'),
            nullable=False,
            server_default='MEASURED'
        ),
        sa.Column('evidence_weight', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['profile_id'], ['text_preference_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_id', 'dimension_key', name='uq_text_profile_dimension_key')
    )
    op.create_index(op.f('ix_text_preference_dimensions_profile_id'), 'text_preference_dimensions', ['profile_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_text_preference_dimensions_profile_id'), table_name='text_preference_dimensions')
    op.drop_table('text_preference_dimensions')

    op.drop_index(op.f('ix_text_preference_profiles_assessment_id'), table_name='text_preference_profiles')
    op.drop_table('text_preference_profiles')

    op.drop_index(op.f('ix_text_preference_responses_assessment_id'), table_name='text_preference_responses')
    op.drop_table('text_preference_responses')

    op.drop_table('preference_assessments')

    text_choice_enum = postgresql.ENUM(
        'STRONGLY_A', 'SLIGHTLY_A', 'NEUTRAL', 'SLIGHTLY_B', 'STRONGLY_B',
        name='text_choice_enum'
    )
    text_choice_enum.drop(op.get_bind(), checkfirst=True)

    preference_dimension_status_enum = postgresql.ENUM(
        'MEASURED', 'NOT_MEASURED',
        name='preference_dimension_status_enum'
    )
    preference_dimension_status_enum.drop(op.get_bind(), checkfirst=True)

    assessment_status_enum = postgresql.ENUM(
        'TEXT_PENDING', 'TEXT_COMPLETE',
        name='assessment_status_enum'
    )
    assessment_status_enum.drop(op.get_bind(), checkfirst=True)
