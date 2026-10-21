"""Analiz tablosu ve sahiplik kanıtı; eski verilere erişim yetkisi verilmez.
Revision ID: 2026_10_21_018
Revises: 2026_08_17_017
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "2026_10_21_018"
down_revision = "2026_08_17_017"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("upload_analyses"):
        if bind.dialect.name == "postgresql":
            state = postgresql.ENUM("PROCESSING", "COMPLETED", "FAILED", "BLOCKED_BY_QUALITY",
                name="upload_analysis_status_enum", create_type=False)
            postgresql.ENUM("PROCESSING", "COMPLETED", "FAILED", "BLOCKED_BY_QUALITY",
                name="upload_analysis_status_enum").create(bind, checkfirst=True)
        else:
            state = sa.Enum("PROCESSING", "COMPLETED", "FAILED", "BLOCKED_BY_QUALITY",
                native_enum=False, name="upload_analysis_status_enum")
        op.create_table("upload_analyses",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("original_sha256", sa.String(64), nullable=False),
            sa.Column("owner_token_sha256", sa.String(64), nullable=True),
            sa.Column("prepared_sha256", sa.String(64), nullable=True),
            sa.Column("image_path", sa.String(512), nullable=True),
            sa.Column("mime_type", sa.String(64), nullable=False),
            sa.Column("quality_status", sa.String(32), nullable=False),
            sa.Column("status", state, nullable=False),
            sa.Column("style_dna_result", sa.JSON(), nullable=True),
            sa.Column("color_result", sa.JSON(), nullable=True),
            sa.Column("vlm_result", sa.JSON(), nullable=True),
            sa.Column("unified_result", sa.JSON(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_upload_analyses_original_sha256", "upload_analyses", ["original_sha256"])
        op.create_index("ix_upload_analyses_status", "upload_analyses", ["status"])
    else:
        existing_cols = {col["name"] for col in inspector.get_columns("upload_analyses")}
        if "owner_token_sha256" not in existing_cols:
            op.add_column("upload_analyses", sa.Column("owner_token_sha256", sa.String(64), nullable=True))

def downgrade() -> None:
    # Geri alma veri kaybettirmez: eski tablonun kendisi korunur.
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("upload_analyses") and any(
        col["name"] == "owner_token_sha256" for col in inspector.get_columns("upload_analyses")
    ):
        op.drop_column("upload_analyses", "owner_token_sha256")
