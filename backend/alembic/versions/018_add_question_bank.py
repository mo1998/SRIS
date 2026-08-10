"""Question bank table

Revision ID: 018_add_question_bank
Revises: 017_add_invitation_reminders
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '018_add_question_bank'
down_revision = '017_add_invitation_reminders'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent + dialect-safe: SQLite has no SERIAL, and table/index
    # existence must be probed via the inspector rather than raw DDL.
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table('question_bank_entries'):
        dialect = bind.dialect.name
        if dialect == "postgresql":
            op.execute("""
                CREATE TABLE question_bank_entries (
                    id SERIAL PRIMARY KEY,
                    owner_id INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    expected_answer TEXT,
                    question_type VARCHAR(50) NOT NULL DEFAULT 'text',
                    options TEXT,
                    weight FLOAT NOT NULL DEFAULT 1.0,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    FOREIGN KEY(owner_id) REFERENCES users(id)
                )
            """)
        else:
            op.execute("""
                CREATE TABLE question_bank_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    expected_answer TEXT,
                    question_type VARCHAR(50) NOT NULL DEFAULT 'text',
                    options TEXT,
                    weight FLOAT NOT NULL DEFAULT 1.0,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    FOREIGN KEY(owner_id) REFERENCES users(id)
                )
            """)
        existing_indexes = {i["name"] for i in inspector.get_indexes('question_bank_entries')}
        if 'ix_question_bank_entries_owner_id' not in existing_indexes:
            op.create_index('ix_question_bank_entries_owner_id', 'question_bank_entries', ['owner_id'])


def downgrade() -> None:
    op.drop_table('question_bank_entries')
