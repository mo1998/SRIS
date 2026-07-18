"""Add revoked invitation status

Revision ID: 007_add_revoked_invitation_status
Revises: 006_add_template_rubric_criteria
Create Date: 2026-07-18 00:00:00.000000

"""
from alembic import op


revision = '007_add_revoked_invitation_status'
down_revision = '006_add_template_rubric_criteria'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE invitationstatus ADD VALUE IF NOT EXISTS 'revoked'")


def downgrade() -> None:
    pass