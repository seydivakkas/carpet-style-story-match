"""add manufacturer brand registry and brand_id on carpets

Revision ID: 2026_08_16_015
Revises: 2026_08_15_014
Create Date: 2026-08-16 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_16_015"
down_revision: Union[str, None] = "2026_08_15_014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create manufacturer_brands table
    op.create_table(
        'manufacturer_brands',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('brand_key', sa.String(length=100), nullable=False),
        sa.Column('brand_name', sa.String(length=255), nullable=False),
        sa.Column('brand_website', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('parser_module', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('brand_key', name='uq_manufacturer_brands_brand_key')
    )
    op.create_index(op.f('ix_manufacturer_brands_brand_key'), 'manufacturer_brands', ['brand_key'], unique=True)

    # 2. Add brand_id to carpets table with batch mode for SQLite support
    with op.batch_alter_table('carpets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('brand_id', postgresql.UUID(as_uuid=True), nullable=True))
        batch_op.create_foreign_key(
            'fk_carpets_brand_id',
            'manufacturer_brands',
            ['brand_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index(op.f('ix_carpets_brand_id'), ['brand_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('carpets', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_carpets_brand_id'))
        batch_op.drop_constraint('fk_carpets_brand_id', type_='foreignkey')
        batch_op.drop_column('brand_id')

    op.drop_index(op.f('ix_manufacturer_brands_brand_key'), table_name='manufacturer_brands')
    op.drop_table('manufacturer_brands')
