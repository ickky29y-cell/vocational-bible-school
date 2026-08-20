"""add forced password change

Revision ID: be8f7a6c5d4e
Revises: ad7e6f5b4c3d
Create Date: 2026-08-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'be8f7a6c5d4e'
down_revision = 'ad7e6f5b4c3d'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if 'must_change_password' not in {column['name'] for column in inspect(bind).get_columns('users')}:
        op.add_column('users', sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    bind = op.get_bind()
    if 'must_change_password' in {column['name'] for column in inspect(bind).get_columns('users')}:
        op.drop_column('users', 'must_change_password')
