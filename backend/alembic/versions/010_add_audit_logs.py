"""Add audit logs

Revision ID: 010_add_audit_logs
Revises: 009_add_user_token_version
Create Date: 2026-07-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '010_add_audit_logs'
down_revision = '009_add_user_token_version'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=100), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor_user_id'), 'audit_logs', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_organization_id'), 'audit_logs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_target_id'), 'audit_logs', ['target_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_target_type'), 'audit_logs', ['target_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_target_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_target_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_organization_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')