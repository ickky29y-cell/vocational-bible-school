"""Initial stub migration (missing revision referenced in DB)

Revision ID: 0cd590792cca
Revises: 
Create Date: 2026-08-17 11:50:00.000000

This is a no-op migration created to satisfy the Alembic revision
referenced by the database but missing from the repository. It does
not modify the schema.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0cd590792cca'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # no-op: placeholder for missing revision referenced by DB
    pass


def downgrade():
    # no-op
    pass
