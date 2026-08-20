"""Add class categories, teacher_classes and exam_classes associations

Revision ID: 2f3b4c5d6e7f
Revises: 11a0f26057cc
Create Date: 2026-08-17 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f3b4c5d6e7f'
down_revision = '11a0f26057cc'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Create class_categories table
    if not inspector.has_table('class_categories'):
        op.create_table(
            'class_categories',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(100), nullable=False, unique=True),
            sa.Column('min_age', sa.Integer(), nullable=True),
            sa.Column('max_age', sa.Integer(), nullable=True),
            sa.Column('assessment_method', sa.String(20), nullable=True),
            sa.Column('description', sa.String(255), nullable=True),
        )

    # Add category_id column to classes if missing
    cols = [c['name'] for c in inspector.get_columns('classes')] if inspector.has_table('classes') else []
    if 'category_id' not in cols and inspector.has_table('classes'):
        op.add_column('classes', sa.Column('category_id', sa.Integer(), nullable=True))
        op.create_foreign_key('classes_category_fk', 'classes', 'class_categories', ['category_id'], ['id'])

    # Create teacher_classes association table
    if not inspector.has_table('teacher_classes'):
        op.create_table(
            'teacher_classes',
            sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('teacher_profiles.id'), primary_key=True),
            sa.Column('class_id', sa.Integer(), sa.ForeignKey('classes.id'), primary_key=True),
        )

    # Create exam_classes association table
    if not inspector.has_table('exam_classes'):
        op.create_table(
            'exam_classes',
            sa.Column('exam_id', sa.Integer(), sa.ForeignKey('exams.id'), primary_key=True),
            sa.Column('class_id', sa.Integer(), sa.ForeignKey('classes.id'), primary_key=True),
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table('exam_classes'):
        op.drop_table('exam_classes')

    if inspector.has_table('teacher_classes'):
        op.drop_table('teacher_classes')

    # drop FK then column
    if inspector.has_table('classes'):
        cols = [c['name'] for c in inspector.get_columns('classes')]
        if 'category_id' in cols:
            try:
                op.drop_constraint('classes_category_fk', 'classes', type_='foreignkey')
            except Exception:
                pass
            op.drop_column('classes', 'category_id')

    if inspector.has_table('class_categories'):
        op.drop_table('class_categories')
