"""Add template rubric criteria

Revision ID: 006_add_template_rubric_criteria
Revises: 005_add_question_rubric_criteria
Create Date: 2026-07-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '006_add_template_rubric_criteria'
down_revision = '005_add_question_rubric_criteria'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'template_rubric_criteria',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_question_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['template_question_id'], ['template_questions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_template_rubric_criteria_id'), 'template_rubric_criteria', ['id'], unique=False)
    op.execute(
        """
        INSERT INTO template_rubric_criteria (template_question_id, name, description, weight, order_index)
        SELECT id, 'Clarity', 'Answer is clear, direct, and easy to evaluate.', 1.0, 0
        FROM template_questions
        """
    )
    op.execute(
        """
        INSERT INTO template_rubric_criteria (template_question_id, name, description, weight, order_index)
        SELECT id, 'Completeness', 'Answer covers the key points expected for this question.', 1.0, 1
        FROM template_questions
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_template_rubric_criteria_id'), table_name='template_rubric_criteria')
    op.drop_table('template_rubric_criteria')