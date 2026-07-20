"""Add evaluation runs and scores

Revision ID: 008_add_evaluation_runs
Revises: 007_add_revoked_invitation_status
Create Date: 2026-07-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '008_add_evaluation_runs'
down_revision = '007_add_revoked_invitation_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('response_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('provider_version', sa.String(length=50), nullable=True),
        sa.Column('model_name', sa.String(length=255), nullable=True),
        sa.Column('config_hash', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('raw_summary', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['response_id'], ['candidate_responses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evaluation_runs_id'), 'evaluation_runs', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_response_id'), 'evaluation_runs', ['response_id'], unique=False)

    op.create_table(
        'evaluation_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('evaluation_run_id', sa.Integer(), nullable=False),
        sa.Column('question_answer_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('feedback_en', sa.Text(), nullable=True),
        sa.Column('feedback_ar', sa.Text(), nullable=True),
        sa.Column('evidence_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['evaluation_run_id'], ['evaluation_runs.id']),
        sa.ForeignKeyConstraint(['question_answer_id'], ['question_answers.id']),
        sa.ForeignKeyConstraint(['question_id'], ['interview_questions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evaluation_scores_evaluation_run_id'), 'evaluation_scores', ['evaluation_run_id'], unique=False)
    op.create_index(op.f('ix_evaluation_scores_id'), 'evaluation_scores', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_evaluation_scores_id'), table_name='evaluation_scores')
    op.drop_index(op.f('ix_evaluation_scores_evaluation_run_id'), table_name='evaluation_scores')
    op.drop_table('evaluation_scores')
    op.drop_index(op.f('ix_evaluation_runs_response_id'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_id'), table_name='evaluation_runs')
    op.drop_table('evaluation_runs')