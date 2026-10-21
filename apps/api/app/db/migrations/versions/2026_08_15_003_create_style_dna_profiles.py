"""create style dna profiles and dimensions tables

Revision ID: 2026_08_15_003
Revises: 2026_08_15_002
Create Date: 2026-08-15 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_003"
down_revision: Union[str, None] = "2026_08_15_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Tekilleştirilmiş PostgreSQL enum oluşturma.
    if op.get_bind().dialect.name == 'postgresql':
        postgresql.ENUM('COMPLETE', 'PARTIAL', 'FAILED', name='style_profile_status_enum').create(op.get_bind(), checkfirst=True)
        postgresql.ENUM('AVAILABLE', 'LOW_CONFIDENCE', 'NOT_AVAILABLE', 'FAILED', name='style_dimension_status_enum').create(op.get_bind(), checkfirst=True)

    # Create enums
    style_profile_status_enum = postgresql.ENUM(
        'COMPLETE', 'PARTIAL', 'FAILED',
        name='style_profile_status_enum',
        create_type=False
    )
    style_profile_status_enum.create(op.get_bind(), checkfirst=True)

    style_dimension_status_enum = postgresql.ENUM(
        'AVAILABLE', 'LOW_CONFIDENCE', 'NOT_AVAILABLE', 'FAILED',
        name='style_dimension_status_enum',
        create_type=False
    )
    style_dimension_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'carpet_style_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('carpet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('algorithm_version', sa.String(length=50), nullable=False, server_default='style-dna-v1.0.0'),
        sa.Column('analysis_input_sha256', sa.String(length=64), nullable=False),
        sa.Column('analysis_scope', sa.String(length=50), nullable=False, server_default='FULL_IMAGE'),
        sa.Column(
            'status',
            postgresql.ENUM('COMPLETE', 'PARTIAL', 'FAILED', name='style_profile_status_enum', create_type=False),
            nullable=False,
            server_default='COMPLETE'
        ),
        sa.Column('analyzed_width_px', sa.Integer(), nullable=False),
        sa.Column('analyzed_height_px', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['carpet_id'], ['carpets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['image_id'], ['carpet_images.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('image_id', 'algorithm_version', name='uq_profile_image_algorithm')
    )
    op.create_index(op.f('ix_carpet_style_profiles_carpet_id'), 'carpet_style_profiles', ['carpet_id'], unique=False)
    op.create_index(op.f('ix_carpet_style_profiles_image_id'), 'carpet_style_profiles', ['image_id'], unique=False)

    op.create_table(
        'carpet_style_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dimension_key', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column(
            'status',
            postgresql.ENUM('AVAILABLE', 'LOW_CONFIDENCE', 'NOT_AVAILABLE', 'FAILED', name='style_dimension_status_enum', create_type=False),
            nullable=False,
            server_default='AVAILABLE'
        ),
        sa.Column('evidence', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('method_version', sa.String(length=50), nullable=False, server_default='v1'),
        sa.ForeignKeyConstraint(['profile_id'], ['carpet_style_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_id', 'dimension_key', name='uq_profile_dimension_key')
    )
    op.create_index(op.f('ix_carpet_style_dimensions_profile_id'), 'carpet_style_dimensions', ['profile_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_carpet_style_dimensions_profile_id'), table_name='carpet_style_dimensions')
    op.drop_table('carpet_style_dimensions')

    op.drop_index(op.f('ix_carpet_style_profiles_image_id'), table_name='carpet_style_profiles')
    op.drop_index(op.f('ix_carpet_style_profiles_carpet_id'), table_name='carpet_style_profiles')
    op.drop_table('carpet_style_profiles')

    style_dimension_status_enum = postgresql.ENUM(
        'AVAILABLE', 'LOW_CONFIDENCE', 'NOT_AVAILABLE', 'FAILED',
        name='style_dimension_status_enum'
    )
    style_dimension_status_enum.drop(op.get_bind(), checkfirst=True)

    style_profile_status_enum = postgresql.ENUM(
        'COMPLETE', 'PARTIAL', 'FAILED',
        name='style_profile_status_enum'
    )
    style_profile_status_enum.drop(op.get_bind(), checkfirst=True)
