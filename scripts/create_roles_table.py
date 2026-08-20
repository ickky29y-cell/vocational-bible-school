import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pkg import app, db
import sqlalchemy as sa

with app.app_context():
    conn = db.engine.connect()
    try:
        stmt = sa.text('''
        CREATE TABLE IF NOT EXISTS roles (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            description VARCHAR(255)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        conn.execute(stmt)
        print('Created or verified roles table')
    except Exception as e:
        print('Failed to create roles table:', e)
    finally:
        conn.close()
