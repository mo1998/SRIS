"""Question bank table

Revision ID: 018_add_question_bank
Revises: 017_add_invitation_reminders
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '018_add_question_bank'
down_revision = '017_add_invitation_reminders'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'question_bank_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('expected_answer', sa.Text(), nullable=True),
        sa.Column('question_type', sa.String(50), nullable=False, server_default='text'),
        sa.Column('options', sa.Text(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('question_bank_entries')
