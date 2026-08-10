"""Add integrity_events table

Revision ID: 016_add_integrity_events
Revises: 015_add_video_file_path
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '016_add_integrity_events'
down_revision = '015_add_video_file_path'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent + dialect-safe: SQLite has no SERIAL, and table/index
    # existence must be probed via the inspector rather than raw DDL.
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table('integrity_events'):
        dialect = bind.dialect.name
        if dialect == "postgresql":
            op.execute("""
                CREATE TABLE integrity_events (
                    id SERIAL PRIMARY KEY,
                    response_id INTEGER NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    FOREIGN KEY(response_id) REFERENCES candidate_responses(id)
                )
            """)
        else:
            op.execute("""
                CREATE TABLE integrity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    response_id INTEGER NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    FOREIGN KEY(response_id) REFERENCES candidate_responses(id)
                )
            """)
    existing_indexes = {i["name"] for i in inspector.get_indexes('integrity_events')}
    if 'ix_integrity_events_response_id' not in existing_indexes:
        op.create_index('ix_integrity_events_response_id', 'integrity_events', ['response_id'])
    if 'ix_integrity_events_event_type' not in existing_indexes:
        op.create_index('ix_integrity_events_event_type', 'integrity_events', ['event_type'])


def downgrade() -> None:
    op.drop_table('integrity_events')
