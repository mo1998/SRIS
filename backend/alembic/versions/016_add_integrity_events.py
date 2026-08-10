"""Add integrity_events table

Revision ID: 016_add_integrity_events
Revises: 015_add_video_file_path
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '016_add_integrity_events'
down_revision = '015_add_video_file_path'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'integrity_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('response_id', sa.Integer(), sa.ForeignKey('candidate_responses.id'), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('integrity_events')
