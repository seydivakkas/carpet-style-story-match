"""Analiz saklama süresi: mevcut kayıtlar otomatik silinmez.

Revision ID: 2026_10_21_019
Revises: 2026_10_21_018
"""
from alembic import op
import sqlalchemy as sa
revision = "2026_10_21_019"
down_revision = "2026_10_21_018"
branch_labels = None
depends_on = None

def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("upload_analyses"):
        raise RuntimeError("019 öncesi 018 upload_analyses migration uygulanmalıdır.")
    cols = {c["name"] for c in inspector.get_columns("upload_analyses")}
    if "expires_at" not in cols:
        op.add_column("upload_analyses", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    idx = {i["name"] for i in inspector.get_indexes("upload_analyses")}
    if "ix_upload_analyses_expires_at" not in idx:
        op.create_index("ix_upload_analyses_expires_at", "upload_analyses", ["expires_at"])

def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("upload_analyses"):
        idx = {i["name"] for i in inspector.get_indexes("upload_analyses")}
        if "ix_upload_analyses_expires_at" in idx:
            op.drop_index("ix_upload_analyses_expires_at", table_name="upload_analyses")
        cols = {c["name"] for c in inspector.get_columns("upload_analyses")}
        if "expires_at" in cols:
            op.drop_column("upload_analyses", "expires_at")
