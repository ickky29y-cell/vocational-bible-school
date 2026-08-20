import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pkg import app, db
import sqlalchemy as sa

with app.app_context():
    conn = db.engine.connect()
    try:
        stmt = sa.text('''
        CREATE TABLE IF NOT EXISTS users (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(120) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role_id INT NOT NULL,
            is_active BOOL DEFAULT TRUE,
            created_at DATETIME,
            last_login_at DATETIME,
            profile_photo VARCHAR(255) DEFAULT 'default-avatar.png',
            INDEX (role_id),
            CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        conn.execute(stmt)
        print('Created or verified users table')
    except Exception as e:
        print('Failed to create users table:', e)
    finally:
        conn.close()
