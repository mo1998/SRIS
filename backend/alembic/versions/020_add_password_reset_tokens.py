"""Password reset tokens table

Revision ID: 020_add_password_reset_tokens
Revises: 019_add_notifications
Create Date: 2026-08-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '020_add_password_reset_tokens'
down_revision = '019_add_notifications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent + dialect-safe: SQLite has no SERIAL, and table/index
    # existence must be probed via the inspector rather than raw DDL.
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table('password_reset_tokens'):
        dialect = bind.dialect.name
        if dialect == "postgresql":
            op.execute("""
                CREATE TABLE password_reset_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    token_hash VARCHAR(255) NOT NULL UNIQUE,
                    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    used_at TIMESTAMP WITHOUT TIME ZONE,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
        else:
            op.execute("""
                CREATE TABLE password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash VARCHAR(255) NOT NULL UNIQUE,
                    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    used_at TIMESTAMP WITHOUT TIME ZONE,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
        existing_indexes = {i["name"] for i in inspector.get_indexes('password_reset_tokens')}
        if 'ix_password_reset_tokens_user_id' not in existing_indexes:
            op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
        if 'ix_password_reset_tokens_token_hash' not in existing_indexes:
            op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'])
        if 'ix_password_reset_tokens_id' not in existing_indexes:
            op.create_index('ix_password_reset_tokens_id', 'password_reset_tokens', ['id'])


def downgrade() -> None:
    op.drop_table('password_reset_tokens')