import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pkg import db, app
import sqlalchemy as sa

with app.app_context():
    conn = db.engine.connect()
    try:
        res = conn.execute(sa.text('SELECT * FROM alembic_version'))
        print('alembic_version rows:')
        for row in res:
            print(row)
    except Exception as e:
        print('Failed to read alembic_version:', e)
    finally:
        conn.close()
