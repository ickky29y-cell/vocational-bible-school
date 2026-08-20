"""repair optional skill foreign keys

Revision ID: ad7e6f5b4c3d
Revises: 9c8d7e6f5a4b
Create Date: 2026-08-20

"""
from alembic import op
from sqlalchemy import inspect


revision = 'ad7e6f5b4c3d'
down_revision = '9c8d7e6f5a4b'
branch_labels = None
depends_on = None


def _has_skill_fk(bind, table_name):
    return any(
        fk.get('referred_table') == 'skills' and fk.get('constrained_columns') == ['skill_id']
        for fk in inspect(bind).get_foreign_keys(table_name)
    )


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        return
    if not _has_skill_fk(bind, 'student_profiles'):
        op.create_foreign_key('fk_student_profiles_skill_id', 'student_profiles', 'skills', ['skill_id'], ['id'])
    if not _has_skill_fk(bind, 'question_banks'):
        op.create_foreign_key('fk_question_banks_skill_id', 'question_banks', 'skills', ['skill_id'], ['id'])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        return
    if _has_skill_fk(bind, 'question_banks'):
        op.drop_constraint('fk_question_banks_skill_id', 'question_banks', type_='foreignkey')
    if _has_skill_fk(bind, 'student_profiles'):
        op.drop_constraint('fk_student_profiles_skill_id', 'student_profiles', type_='foreignkey')
