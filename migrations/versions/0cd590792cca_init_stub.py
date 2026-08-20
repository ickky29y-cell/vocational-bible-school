"""Initial stub migration (missing revision referenced in DB)

Revision ID: 0cd590792cca
Revises: 
Create Date: 2026-08-17 11:50:00.000000

This baseline creates the model schema for fresh databases. The repository
originally treated this revision as a no-op, which left fresh deployments
without base tables such as exam_attempts.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0cd590792cca'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # The original baseline was missing from the repository. Creating the
    # model metadata here lets later migrations safely apply incremental fixes.
    from pkg import db

    db.metadata.create_all(bind=op.get_bind())


def downgrade():
    # no-op
    pass
