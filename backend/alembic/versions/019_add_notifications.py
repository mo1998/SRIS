"""In-app notifications table

Revision ID: 019_add_notifications
Revises: 018_add_question_bank
Create Date: 2026-08-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '019_add_notifications'
down_revision = '018_add_question_bank'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent + dialect-safe: SQLite has no SERIAL, and table/index
    # existence must be probed via the inspector rather than raw DDL.
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table('notifications'):
        dialect = bind.dialect.name
        if dialect == "postgresql":
            op.execute("""
                CREATE TABLE notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    type VARCHAR(50) NOT NULL DEFAULT 'general',
                    title VARCHAR(255) NOT NULL,
                    message TEXT,
                    link VARCHAR(255),
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
        else:
            op.execute("""
                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type VARCHAR(50) NOT NULL DEFAULT 'general',
                    title VARCHAR(255) NOT NULL,
                    message TEXT,
                    link VARCHAR(255),
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
        existing_indexes = {i["name"] for i in inspector.get_indexes('notifications')}
        if 'ix_notifications_user_id' not in existing_indexes:
            op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
        if 'ix_notifications_id' not in existing_indexes:
            op.create_index('ix_notifications_id', 'notifications', ['id'])


def downgrade() -> None:
    op.drop_table('notifications')