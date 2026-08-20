from pkg import app, db
from sqlalchemy import inspect, text

print('URI', app.config['SQLALCHEMY_DATABASE_URI'])
with app.app_context():
    inspector = inspect(db.engine)
    print('DIALECT', db.engine.dialect.name)
    if not inspector.has_table('exam_section_bank_rules'):
        print('TABLE_MISSING')
    else:
        print('COLUMNS', inspector.get_columns('exam_section_bank_rules'))
        if db.engine.dialect.name == 'mysql':
            print('DDL', db.session.execute(text('SHOW CREATE TABLE exam_section_bank_rules')).fetchone()[1])
