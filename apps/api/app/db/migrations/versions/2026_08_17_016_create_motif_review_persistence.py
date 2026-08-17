"""create motif review persistence tables

Revision ID: 2026_08_17_016
Revises: 2026_08_16_015
Create Date: 2026-08-17 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2026_08_17_016"
down_revision: Union[str, None] = "2026_08_16_015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create motif_review_subjects table
    op.create_table(
        'motif_review_subjects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('review_subject_id', sa.String(length=100), nullable=False),
        sa.Column('analysis_id', sa.String(length=100), nullable=False),
        sa.Column('candidate_id', sa.String(length=100), nullable=False),
        sa.Column('image_asset_id', sa.String(length=100), nullable=True),
        sa.Column('visual_candidate_key', sa.String(length=100), nullable=False),
        sa.Column('proposed_canonical_motif_key', sa.String(length=100), nullable=True),
        sa.Column('original_candidate_status', sa.String(length=50), nullable=False),
        sa.Column('candidate_confidence', sa.Float(), nullable=False),
        sa.Column('candidate_snapshot', sa.JSON(), nullable=False),
        sa.Column('snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('model_provenance', sa.JSON(), nullable=False),
        sa.Column('ontology_version', sa.String(length=50), nullable=False, server_default='motif-ontology-v1.0.0'),
        sa.Column('review_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('review_subject_id', name='uq_motif_review_subject_public_id'),
        sa.UniqueConstraint('analysis_id', 'candidate_id', name='uq_motif_review_subject_identity')
    )
    op.create_index(op.f('ix_motif_review_subjects_review_subject_id'), 'motif_review_subjects', ['review_subject_id'], unique=True)
    op.create_index(op.f('ix_motif_review_subjects_analysis_id'), 'motif_review_subjects', ['analysis_id'], unique=False)

    # 2. Create motif_review_events table
    op.create_table(
        'motif_review_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('review_id', sa.String(length=100), nullable=False),
        sa.Column('review_subject_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('resulting_status', sa.String(length=30), nullable=False),
        sa.Column('selected_canonical_motif_key', sa.String(length=100), nullable=True),
        sa.Column('reason_code', sa.String(length=50), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('reviewer_ref', sa.String(length=255), nullable=False),
        sa.Column('reviewer_boundary', sa.String(length=50), nullable=False, server_default='GATEWAY_TRUSTED'),
        sa.Column('candidate_snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('supersedes_review_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['review_subject_id'], ['motif_review_subjects.id'], ondelete='RESTRICT', name='fk_motif_review_events_subject_id'),
        sa.ForeignKeyConstraint(['supersedes_review_id'], ['motif_review_events.id'], ondelete='RESTRICT', name='fk_motif_review_events_supersedes_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('review_id', name='uq_motif_review_event_public_id'),
        sa.UniqueConstraint('review_subject_id', 'idempotency_key', name='uq_motif_review_event_idempotency'),
        sa.UniqueConstraint('review_subject_id', 'version', name='uq_motif_review_event_version')
    )
    op.create_index(op.f('ix_motif_review_events_review_id'), 'motif_review_events', ['review_id'], unique=True)
    op.create_index(op.f('ix_motif_review_events_review_subject_id'), 'motif_review_events', ['review_subject_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_motif_review_events_review_subject_id'), table_name='motif_review_events')
    op.drop_index(op.f('ix_motif_review_events_review_id'), table_name='motif_review_events')
    op.drop_table('motif_review_events')

    op.drop_index(op.f('ix_motif_review_subjects_analysis_id'), table_name='motif_review_subjects')
    op.drop_index(op.f('ix_motif_review_subjects_review_subject_id'), table_name='motif_review_subjects')
    op.drop_table('motif_review_subjects')
