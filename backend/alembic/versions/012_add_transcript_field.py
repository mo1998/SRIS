"""Add transcript field to question_answers

Revision ID: 012_add_transcript_field
Revises: 011_add_reviewer_decision_scorecard
Create Date: 2026-07-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '012_add_transcript_field'
down_revision = '011_add_reviewer_decision_scorecard'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('question_answers', sa.Column('transcript', sa.Text(), nullable=True))
    op.add_column('question_answers', sa.Column('transcript_updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('question_answers', 'transcript_updated_at')
    op.drop_column('question_answers', 'transcript')
