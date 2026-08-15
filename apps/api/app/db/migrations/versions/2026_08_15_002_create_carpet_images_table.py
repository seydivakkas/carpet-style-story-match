"""create carpet images table

Revision ID: 2026_08_15_002
Revises: 2026_08_15_001
Create Date: 2026-08-15 18:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_002"
down_revision: Union[str, None] = "2026_08_15_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'carpet_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('carpet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('storage_backend', sa.String(length=50), nullable=False, server_default='LOCAL_FILESYSTEM'),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('byte_size', sa.BigInteger(), nullable=False),
        sa.Column('width_px', sa.Integer(), nullable=False),
        sa.Column('height_px', sa.Integer(), nullable=False),
        sa.Column('channels', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['carpet_id'], ['carpets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_key'),
        sa.UniqueConstraint('carpet_id', 'sha256', name='uq_carpet_image_sha256')
    )
    op.create_index(op.f('ix_carpet_images_carpet_id'), 'carpet_images', ['carpet_id'], unique=False)
    op.create_index('ix_carpet_images_carpet_id_is_primary', 'carpet_images', ['carpet_id', 'is_primary'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_carpet_images_carpet_id_is_primary', table_name='carpet_images')
    op.drop_index(op.f('ix_carpet_images_carpet_id'), table_name='carpet_images')
    op.drop_table('carpet_images')
