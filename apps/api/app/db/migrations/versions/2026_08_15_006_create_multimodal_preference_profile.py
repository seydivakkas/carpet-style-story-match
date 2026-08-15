"""create multimodal preference profile and confidence profile tables

Revision ID: 2026_08_15_006
Revises: 2026_08_15_005
Create Date: 2026-08-15 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_006"
down_revision: Union[str, None] = "2026_08_15_005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE assessment_status_enum ADD VALUE IF NOT EXISTS 'PROFILE_READY';")
        op.execute("ALTER TYPE assessment_status_enum ADD VALUE IF NOT EXISTS 'PROFILE_REVIEWED';")

    user_profile_status_enum = postgresql.ENUM('DRAFT', 'REVIEWED', name='user_profile_status_enum', create_type=False)
    user_profile_status_enum.create(bind, checkfirst=True)

    user_preference_provenance_enum = postgresql.ENUM('INFERRED', 'USER_CONFIRMED', 'USER_OVERRIDDEN', name='user_preference_provenance_enum', create_type=False)
    user_preference_provenance_enum.create(bind, checkfirst=True)

    confidence_status_enum = postgresql.ENUM('AVAILABLE', 'NO_EVIDENCE', name='confidence_status_enum', create_type=False)
    confidence_status_enum.create(bind, checkfirst=True)

    # 1. user_preference_profiles
    op.create_table(
        'user_preference_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_version', sa.String(length=50), nullable=False, server_default='multimodal-preference-v1'),
        sa.Column('status', sa.Enum('DRAFT', 'REVIEWED', name='user_profile_status_enum'), nullable=False, server_default='DRAFT'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', name='uq_user_profile_assessment_id'),
        sa.UniqueConstraint('assessment_id', 'profile_version', name='uq_user_profile_assessment_version')
    )
    op.create_index(op.f('ix_user_preference_profiles_assessment_id'), 'user_preference_profiles', ['assessment_id'], unique=True)

    # 2. user_preference_dimensions
    op.create_table(
        'user_preference_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dimension_key', sa.String(length=50), nullable=False),
        sa.Column('inferred_value', sa.Float(), nullable=True),
        sa.Column('final_value', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('MEASURED', 'NOT_MEASURED', name='preference_dimension_status_enum'), nullable=False, server_default='MEASURED'),
        sa.Column('provenance', sa.Enum('INFERRED', 'USER_CONFIRMED', 'USER_OVERRIDDEN', name='user_preference_provenance_enum'), nullable=False, server_default='INFERRED'),
        sa.Column('text_value', sa.Float(), nullable=True),
        sa.Column('text_evidence_weight', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('visual_value', sa.Float(), nullable=True),
        sa.Column('visual_evidence_weight', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['profile_id'], ['user_preference_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_id', 'dimension_key', name='uq_user_profile_dimension_key')
    )
    op.create_index(op.f('ix_user_preference_dimensions_profile_id'), 'user_preference_dimensions', ['profile_id'], unique=False)

    # 3. preference_confidence_profiles
    op.create_table(
        'preference_confidence_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('preference_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('confidence_version', sa.String(length=50), nullable=False, server_default='preference-confidence-v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['preference_assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['preference_profile_id'], ['user_preference_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('preference_profile_id', name='uq_confidence_preference_profile_id')
    )
    op.create_index(op.f('ix_preference_confidence_profiles_assessment_id'), 'preference_confidence_profiles', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_preference_confidence_profiles_preference_profile_id'), 'preference_confidence_profiles', ['preference_profile_id'], unique=True)

    # 4. preference_confidence_dimensions
    op.create_table(
        'preference_confidence_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('confidence_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dimension_key', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('AVAILABLE', 'NO_EVIDENCE', name='confidence_status_enum'), nullable=False, server_default='AVAILABLE'),
        sa.Column('modality_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('agreement', sa.Float(), nullable=True),
        sa.Column('source_coverage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('evidence_json', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['confidence_profile_id'], ['preference_confidence_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('confidence_profile_id', 'dimension_key', name='uq_confidence_profile_dimension_key')
    )
    op.create_index(op.f('ix_preference_confidence_dimensions_confidence_profile_id'), 'preference_confidence_dimensions', ['confidence_profile_id'], unique=False)

def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index(op.f('ix_preference_confidence_dimensions_confidence_profile_id'), table_name='preference_confidence_dimensions')
    op.drop_table('preference_confidence_dimensions')

    op.drop_index(op.f('ix_preference_confidence_profiles_preference_profile_id'), table_name='preference_confidence_profiles')
    op.drop_index(op.f('ix_preference_confidence_profiles_assessment_id'), table_name='preference_confidence_profiles')
    op.drop_table('preference_confidence_profiles')

    op.drop_index(op.f('ix_user_preference_dimensions_profile_id'), table_name='user_preference_dimensions')
    op.drop_table('user_preference_dimensions')

    op.drop_index(op.f('ix_user_preference_profiles_assessment_id'), table_name='user_preference_profiles')
    op.drop_table('user_preference_profiles')

    confidence_status_enum = postgresql.ENUM('AVAILABLE', 'NO_EVIDENCE', name='confidence_status_enum')
    confidence_status_enum.drop(bind, checkfirst=True)

    user_preference_provenance_enum = postgresql.ENUM('INFERRED', 'USER_CONFIRMED', 'USER_OVERRIDDEN', name='user_preference_provenance_enum')
    user_preference_provenance_enum.drop(bind, checkfirst=True)

    user_profile_status_enum = postgresql.ENUM('DRAFT', 'REVIEWED', name='user_profile_status_enum')
    user_profile_status_enum.drop(bind, checkfirst=True)
