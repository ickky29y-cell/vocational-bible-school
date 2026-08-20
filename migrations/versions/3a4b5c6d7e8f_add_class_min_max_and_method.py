"""Add min_age, max_age and assessment_method to classes

Revision ID: 3a4b5c6d7e8f
Revises: 2f3b4c5d6e7f
Create Date: 2026-08-17 12:55:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3a4b5c6d7e8f'
down_revision = '2f3b4c5d6e7f'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table('classes'):
        cols = [c['name'] for c in inspector.get_columns('classes')]
        if 'min_age' not in cols:
            op.add_column('classes', sa.Column('min_age', sa.Integer(), nullable=True))
        if 'max_age' not in cols:
            op.add_column('classes', sa.Column('max_age', sa.Integer(), nullable=True))
        if 'assessment_method' not in cols:
            op.add_column('classes', sa.Column('assessment_method', sa.String(20), nullable=True))


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table('classes'):
        cols = [c['name'] for c in inspector.get_columns('classes')]
        if 'assessment_method' in cols:
            op.drop_column('classes', 'assessment_method')
        if 'max_age' in cols:
            op.drop_column('classes', 'max_age')
        if 'min_age' in cols:
            op.drop_column('classes', 'min_age')
