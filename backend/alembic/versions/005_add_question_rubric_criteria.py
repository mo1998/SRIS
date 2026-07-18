"""Add question rubric criteria

Revision ID: 005_add_question_rubric_criteria
Revises: 004_add_interview_templates
Create Date: 2026-07-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '005_add_question_rubric_criteria'
down_revision = '004_add_interview_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rubric_criteria',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['interview_questions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rubric_criteria_id'), 'rubric_criteria', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_rubric_criteria_id'), table_name='rubric_criteria')
    op.drop_table('rubric_criteria')