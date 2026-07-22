"""Add data export requests for GDPR compliance

Revision ID: 013_add_data_export_requests
Revises: 012_add_transcript_field
Create Date: 2026-07-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '013_add_data_export_requests'
down_revision = '012_add_transcript_field'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'data_export_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requester_email', sa.String(255), nullable=False),
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('processed_by', sa.Integer(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_data_export_requests_id'), 'data_export_requests', ['id'], unique=False)
    op.create_index(op.f('ix_data_export_requests_requester_email'), 'data_export_requests', ['requester_email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_data_export_requests_requester_email'), table_name='data_export_requests')
    op.drop_index(op.f('ix_data_export_requests_id'), table_name='data_export_requests')
    op.drop_table('data_export_requests')
