"""Add organizations and team memberships

Revision ID: 002_add_organizations
Revises: 001_initial
Create Date: 2026-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '002_add_organizations'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)

    op.create_table(
        'team_memberships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'recruiter', 'reviewer', name='teamrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_team_membership_org_user')
    )
    op.create_index(op.f('ix_team_memberships_id'), 'team_memberships', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_team_memberships_id'), table_name='team_memberships')
    op.drop_table('team_memberships')
    op.drop_index(op.f('ix_organizations_id'), table_name='organizations')
    op.drop_table('organizations')
    op.execute('DROP TYPE teamrole')