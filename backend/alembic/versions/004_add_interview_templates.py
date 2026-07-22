"""Add interview templates

Revision ID: 004_add_interview_templates
Revises: 003_scope_interviews_org
Create Date: 2026-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '004_add_interview_templates'
down_revision = '003_scope_interviews_org'
branch_labels = None
depends_on = None


TEMPLATES = [
    {
        'name': 'Customer Support Screen',
        'description': 'First-round screen for customer support candidates.',
        'role_category': 'customer_support',
        'duration_minutes': 25,
        'pass_score': 70.0,
        'questions': [
            ('How do you handle an upset customer?', 'Listen, empathize, clarify the issue, resolve what can be resolved, and follow up.', 1.5, 0),
            ('Describe a time you turned a negative customer experience around.', 'Provides a specific example with action, communication, and measurable outcome.', 1.0, 1),
        ],
    },
    {
        'name': 'Sales Screen',
        'description': 'Structured first screen for sales candidates.',
        'role_category': 'sales',
        'duration_minutes': 25,
        'pass_score': 70.0,
        'questions': [
            ('How do you qualify a new lead?', 'Identifies customer need, authority, urgency, budget, and next step fit.', 1.5, 0),
            ('Tell us about a deal you lost and what you learned.', 'Reflects ownership, learning, and process improvement.', 1.0, 1),
        ],
    },
    {
        'name': 'Operations Coordinator Screen',
        'description': 'Structured screen for operations coordination roles.',
        'role_category': 'operations',
        'duration_minutes': 30,
        'pass_score': 70.0,
        'questions': [
            ('How do you prioritize competing tasks with the same deadline?', 'Explains triage, stakeholder communication, impact, and follow-through.', 1.5, 0),
            ('Describe a process you improved.', 'Gives a concrete process, improvement action, and result.', 1.0, 1),
        ],
    },
    {
        'name': 'Internship Screen',
        'description': 'General-purpose internship screening template.',
        'role_category': 'internship',
        'duration_minutes': 20,
        'pass_score': 65.0,
        'questions': [
            ('What project or class best prepared you for this role?', 'Connects relevant experience to role requirements with specifics.', 1.0, 0),
            ('How do you approach learning a new tool quickly?', 'Shows curiosity, structured learning, and willingness to ask for feedback.', 1.0, 1),
        ],
    },
    {
        'name': 'Junior Developer Screen',
        'description': 'First-round screen for junior software candidates.',
        'role_category': 'engineering',
        'duration_minutes': 30,
        'pass_score': 70.0,
        'questions': [
            ('Explain a bug you fixed and how you found the root cause.', 'Describes debugging steps, evidence, fix, and verification.', 1.5, 0),
            ('How do you review code before opening a pull request?', 'Mentions tests, readability, edge cases, and self-review.', 1.0, 1),
        ],
    },
]


def upgrade() -> None:
    op.create_table(
        'interview_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('role_category', sa.String(length=100), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('pass_score', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_interview_templates_id'), 'interview_templates', ['id'], unique=False)

    op.create_table(
        'template_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('expected_answer', sa.Text(), nullable=True),
        sa.Column('question_type', sa.String(length=50), nullable=True),
        sa.Column('options', sa.Text(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['interview_templates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_template_questions_id'), 'template_questions', ['id'], unique=False)

    template_table = sa.table(
        'interview_templates',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('role_category', sa.String),
        sa.column('duration_minutes', sa.Integer),
        sa.column('pass_score', sa.Float),
        sa.column('is_active', sa.Boolean),
    )
    question_table = sa.table(
        'template_questions',
        sa.column('template_id', sa.Integer),
        sa.column('question_text', sa.Text),
        sa.column('expected_answer', sa.Text),
        sa.column('question_type', sa.String),
        sa.column('weight', sa.Float),
        sa.column('order_index', sa.Integer),
    )

    for template_id, template in enumerate(TEMPLATES, start=1):
        op.bulk_insert(template_table, [{
            'id': template_id,
            'name': template['name'],
            'description': template['description'],
            'role_category': template['role_category'],
            'duration_minutes': template['duration_minutes'],
            'pass_score': template['pass_score'],
            'is_active': True,
        }])
        op.bulk_insert(question_table, [{
            'template_id': template_id,
            'question_text': question_text,
            'expected_answer': expected_answer,
            'question_type': 'text',
            'weight': weight,
            'order_index': order_index,
        } for question_text, expected_answer, weight, order_index in template['questions']])


def downgrade() -> None:
    op.drop_index(op.f('ix_template_questions_id'), table_name='template_questions')
    op.drop_table('template_questions')
    op.drop_index(op.f('ix_interview_templates_id'), table_name='interview_templates')
    op.drop_table('interview_templates')