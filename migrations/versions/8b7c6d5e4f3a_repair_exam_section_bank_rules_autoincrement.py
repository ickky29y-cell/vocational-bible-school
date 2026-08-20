"""repair exam section bank rules autoincrement

Revision ID: 8b7c6d5e4f3a
Revises: f4fdbc145566
Create Date: 2026-08-20

"""
from alembic import op
from sqlalchemy import inspect, text


revision = '8b7c6d5e4f3a'
down_revision = 'f4fdbc145566'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'mysql':
        return

    inspector = inspect(bind)
    if not inspector.has_table('exam_section_bank_rules'):
        return

    columns = {column['name']: column for column in inspector.get_columns('exam_section_bank_rules')}
    if not columns.get('id', {}).get('autoincrement', False):
        op.execute(text(
            'ALTER TABLE exam_section_bank_rules '
            'MODIFY COLUMN id INTEGER NOT NULL AUTO_INCREMENT'
        ))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'mysql':
        return

    op.execute(text(
        'ALTER TABLE exam_section_bank_rules '
        'MODIFY COLUMN id INTEGER NOT NULL'
    ))
