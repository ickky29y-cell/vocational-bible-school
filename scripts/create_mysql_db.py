import os
import mysql.connector

host = os.environ.get('DATABASE_HOST', 'localhost')
user = os.environ.get('DATABASE_USER', 'root')
password = os.environ.get('DATABASE_PASS', '')
port = int(os.environ.get('DATABASE_PORT', 3306))
dbname = os.environ.get('DATABASE_NAME', 'vvs')

print(f"Connecting to MySQL {user}@{host}:{port} to ensure database '{dbname}' exists...")
cnx = mysql.connector.connect(host=host, user=user, password=password, port=port)
cnx.autocommit = True
cursor = cnx.cursor()
try:
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    print(f"Database '{dbname}' ready.")
except Exception as e:
    print('Failed to create database:', e)
finally:
    cursor.close()
    cnx.close()
