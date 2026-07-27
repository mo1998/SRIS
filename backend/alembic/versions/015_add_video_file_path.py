"""Add video_file_path column to question_answers

Revision ID: 015_add_video_file_path
Revises: 014_add_webhooks
Create Date: 2026-07-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '015_add_video_file_path'
down_revision = '014_add_webhooks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('question_answers', sa.Column('video_file_path', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('question_answers', 'video_file_path')
