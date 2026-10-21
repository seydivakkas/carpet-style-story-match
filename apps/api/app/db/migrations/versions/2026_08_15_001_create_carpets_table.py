"""create carpets table

Revision ID: 2026_08_15_001
Revises:
Create Date: 2026-08-15 18:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_15_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Tekilleştirilmiş PostgreSQL enum oluşturma.
    if op.get_bind().dialect.name == 'postgresql':
        postgresql.ENUM('CATALOG', 'USER_UPLOAD', 'HISTORICAL', 'MANUAL', name='carpet_source_type_enum').create(op.get_bind(), checkfirst=True)

    # Create enum type if postgresql
    carpet_source_type_enum = postgresql.ENUM(
        'CATALOG', 'USER_UPLOAD', 'HISTORICAL', 'MANUAL',
        name='carpet_source_type_enum',
        create_type=False
    )
    carpet_source_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'carpets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('collection', sa.String(length=255), nullable=True),
        sa.Column('width_cm', sa.Float(), nullable=True),
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('material', sa.String(length=255), nullable=True),
        sa.Column('style_label', sa.String(length=100), nullable=True),
        sa.Column(
            'source_type',
            postgresql.ENUM('CATALOG', 'USER_UPLOAD', 'HISTORICAL', 'MANUAL', name='carpet_source_type_enum', create_type=False),
            nullable=False,
            server_default='CATALOG'
        ),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint('width_cm IS NULL OR width_cm > 0', name='ck_carpets_width_positive'),
        sa.CheckConstraint('height_cm IS NULL OR height_cm > 0', name='ck_carpets_height_positive'),
        sa.CheckConstraint('length(trim(name)) > 0', name='ck_carpets_name_not_empty'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_carpets_collection'), 'carpets', ['collection'], unique=False)
    op.create_index(op.f('ix_carpets_manufacturer'), 'carpets', ['manufacturer'], unique=False)
    op.create_index(op.f('ix_carpets_sku'), 'carpets', ['sku'], unique=True)
    op.create_index(op.f('ix_carpets_style_label'), 'carpets', ['style_label'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_carpets_style_label'), table_name='carpets')
    op.drop_index(op.f('ix_carpets_sku'), table_name='carpets')
    op.drop_index(op.f('ix_carpets_manufacturer'), table_name='carpets')
    op.drop_index(op.f('ix_carpets_collection'), table_name='carpets')
    op.drop_table('carpets')
    
    carpet_source_type_enum = postgresql.ENUM(
        'CATALOG', 'USER_UPLOAD', 'HISTORICAL', 'MANUAL',
        name='carpet_source_type_enum'
    )
    carpet_source_type_enum.drop(op.get_bind(), checkfirst=True)
