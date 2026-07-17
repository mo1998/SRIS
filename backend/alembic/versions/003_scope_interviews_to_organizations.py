"""Scope interviews to organizations

Revision ID: 003_scope_interviews_to_organizations
Revises: 002_add_organizations
Create Date: 2026-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '003_scope_interviews_to_organizations'
down_revision = '002_add_organizations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('interviews') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_interviews_organization_id_organizations',
            'organizations',
            ['organization_id'],
            ['id']
        )
    op.execute(
        """
        UPDATE interviews
        SET organization_id = (
            SELECT team_memberships.organization_id
            FROM team_memberships
            WHERE team_memberships.user_id = interviews.employer_id
            ORDER BY team_memberships.created_at ASC
            LIMIT 1
        )
        WHERE organization_id IS NULL
        """
    )


def downgrade() -> None:
    with op.batch_alter_table('interviews') as batch_op:
        batch_op.drop_constraint('fk_interviews_organization_id_organizations', type_='foreignkey')
        batch_op.drop_column('organization_id')