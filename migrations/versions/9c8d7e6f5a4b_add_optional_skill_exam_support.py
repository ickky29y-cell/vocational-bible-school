"""add optional skill exam support

Revision ID: 9c8d7e6f5a4b
Revises: 8b7c6d5e4f3a
Create Date: 2026-08-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '9c8d7e6f5a4b'
down_revision = '8b7c6d5e4f3a'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'skill_id' not in {column['name'] for column in inspector.get_columns('student_profiles')}:
        op.add_column('student_profiles', sa.Column('skill_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_student_profiles_skill_id', 'student_profiles', 'skills', ['skill_id'], ['id'])

    if 'skill_id' not in {column['name'] for column in inspector.get_columns('question_banks')}:
        op.add_column('question_banks', sa.Column('skill_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_question_banks_skill_id', 'question_banks', 'skills', ['skill_id'], ['id'])

    if 'skill_question_count' not in {column['name'] for column in inspector.get_columns('exams')}:
        op.add_column('exams', sa.Column('skill_question_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'skill_question_count' in {column['name'] for column in inspector.get_columns('exams')}:
        op.drop_column('exams', 'skill_question_count')
    if 'skill_id' in {column['name'] for column in inspector.get_columns('question_banks')}:
        op.drop_constraint('fk_question_banks_skill_id', 'question_banks', type_='foreignkey')
        op.drop_column('question_banks', 'skill_id')
    if 'skill_id' in {column['name'] for column in inspector.get_columns('student_profiles')}:
        op.drop_constraint('fk_student_profiles_skill_id', 'student_profiles', type_='foreignkey')
        op.drop_column('student_profiles', 'skill_id')
