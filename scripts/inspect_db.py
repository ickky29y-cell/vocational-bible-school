import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pkg import db, app
import sqlalchemy as sa

with app.app_context():
    engine = db.engine
    with engine.connect() as conn:
        print('Connected to:', engine.url)
        res = conn.execute(sa.text("SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()"))
        tables = list(res)
        print('Tables in database:')
        for t in tables:
            print(' -', t[0], 'engine=', t[1])

        # Try both plural and singular forms for the users table
        for tbl in ('users', 'user'):
            try:
                r = conn.execute(sa.text(f"SHOW CREATE TABLE `{tbl}`"))
                print(f"\nSHOW CREATE TABLE {tbl}:")
                for row in r:
                    print(row)
            except Exception as e:
                print(f"\nSHOW CREATE TABLE {tbl} failed:", e)

        for tbl in ('users', 'user'):
            cols = conn.execute(sa.text(f"SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='{tbl}'"))
            print(f"\n{tbl} table columns:")
            for c in cols:
                print(' -', c)
