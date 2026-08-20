"""Restore data/current_data.json into an empty database.

The command refuses to overwrite an existing database unless --force is
explicitly supplied. Schema creation/migrations should run before this script.
"""
import argparse
import datetime
import decimal
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import inspect, text

from pkg import app, db


parser = argparse.ArgumentParser()
parser.add_argument('--force', action='store_true', help='Allow replacing existing rows')
args = parser.parse_args()

snapshot_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'current_data.json')
with open(snapshot_path, encoding='utf-8') as source:
    snapshot = json.load(source)


def typed_value(column, value):
    if value is None:
        return None
    python_type = getattr(column.type, 'python_type', None)
    if python_type is datetime.datetime:
        return datetime.datetime.fromisoformat(value)
    if python_type is datetime.date:
        return datetime.date.fromisoformat(value)
    if python_type is datetime.time:
        return datetime.time.fromisoformat(value)
    if python_type is decimal.Decimal:
        return decimal.Decimal(value)
    if python_type is bool:
        return bool(value)
    if python_type in (int, float, str):
        return python_type(value)
    return value


with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    existing_rows = sum(
        db.session.execute(text(f'SELECT COUNT(*) FROM `{table_name}`')).scalar()
        for table_name in inspector.get_table_names()
        if table_name != 'alembic_version'
    )
    if existing_rows and not args.force:
        print('DATABASE_NOT_EMPTY=SKIP_RESTORE')
        raise SystemExit(0)

    is_mysql = db.engine.dialect.name == 'mysql'
    with db.engine.begin() as connection:
        if is_mysql:
            connection.execute(text('SET FOREIGN_KEY_CHECKS=0'))
        else:
            connection.execute(text('PRAGMA foreign_keys=OFF'))
        for table_name in reversed(list(snapshot['tables'])):
            if table_name in inspector.get_table_names():
                connection.execute(text(f'DELETE FROM `{table_name}`'))

        for table_name, rows in snapshot['tables'].items():
            table = db.metadata.tables.get(table_name)
            if table is None or not rows:
                continue
            values = [
                {key: typed_value(table.c[key], value) for key, value in row.items()}
                for row in rows
            ]
            for value in values:
                connection.execute(table.insert(), value)
        if is_mysql:
            connection.execute(text('SET FOREIGN_KEY_CHECKS=1'))
        else:
            connection.execute(text('PRAGMA foreign_keys=ON'))

    print(f'RESTORED_TABLES={len(snapshot["tables"])}')