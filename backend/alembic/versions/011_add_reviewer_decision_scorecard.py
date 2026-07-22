"""Add reviewer decision and scorecard

Revision ID: 011_add_reviewer_decision_scorecard
Revises: 010_add_audit_logs
Create Date: 2026-07-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '011_add_reviewer_decision_scorecard'
down_revision = '010_add_audit_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('candidate_responses', sa.Column('reviewer_decision', sa.String(50), server_default='pending', nullable=False))
    op.add_column('candidate_responses', sa.Column('reviewer_decision_at', sa.DateTime(), nullable=True))
    op.add_column('candidate_responses', sa.Column('reviewer_decision_by', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_candidate_responses_reviewer_decision'), 'candidate_responses', ['reviewer_decision'], unique=False)

    op.create_table(
        'reviewer_scorecards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('response_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('strengths', sa.Text(), nullable=True),
        sa.Column('weaknesses', sa.Text(), nullable=True),
        sa.Column('overall_comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['response_id'], ['candidate_responses.id']),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('response_id'),
    )
    op.create_index(op.f('ix_reviewer_scorecards_id'), 'reviewer_scorecards', ['id'], unique=False)
    op.create_index(op.f('ix_reviewer_scorecards_response_id'), 'reviewer_scorecards', ['response_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_reviewer_scorecards_response_id'), table_name='reviewer_scorecards')
    op.drop_index(op.f('ix_reviewer_scorecards_id'), table_name='reviewer_scorecards')
    op.drop_table('reviewer_scorecards')
    op.drop_index(op.f('ix_candidate_responses_reviewer_decision'), table_name='candidate_responses')
    op.drop_column('candidate_responses', 'reviewer_decision_by')
    op.drop_column('candidate_responses', 'reviewer_decision_at')
    op.drop_column('candidate_responses', 'reviewer_decision')
