"""harden reviewer_boundary default

Revision ID: 2026_08_17_017
Revises: 2026_08_17_016
Create Date: 2026-08-17 14:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "2026_08_17_017"
down_revision: Union[str, None] = "2026_08_17_016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('motif_review_events', schema=None) as batch_op:
        batch_op.alter_column(
            'reviewer_boundary',
            existing_type=sa.String(length=50),
            server_default=None,
            existing_nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table('motif_review_events', schema=None) as batch_op:
        batch_op.alter_column(
            'reviewer_boundary',
            existing_type=sa.String(length=50),
            server_default=sa.text("'GATEWAY_TRUSTED'"),
            existing_nullable=False
        )
