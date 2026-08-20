from pkg import app, db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    for table in ('student_profiles', 'question_banks', 'exams'):
        print(table, [column['name'] for column in inspector.get_columns(table)])
        print('FKS', inspector.get_foreign_keys(table))
