"""add class_id to exam_attempts

Revision ID: f4fdbc145566
Revises: 966fbd6c5efe
Create Date: 2026-08-18 00:39:17.559613

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4fdbc145566'
down_revision = '966fbd6c5efe'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('exam_attempts'):
        return

    columns = {column['name'] for column in inspector.get_columns('exam_attempts')}
    if 'class_id' in columns:
        return

    with op.batch_alter_table('exam_attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('class_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'classes', ['class_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('exam_attempts'):
        return

    columns = {column['name'] for column in inspector.get_columns('exam_attempts')}
    if 'class_id' not in columns:
        return

    with op.batch_alter_table('exam_attempts', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('class_id')

    # ### end Alembic commands ###
