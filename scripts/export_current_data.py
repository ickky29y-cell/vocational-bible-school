"""Export the current database contents for a fresh deployment.

Run with the intended database environment variables set. The generated
snapshot is data/current_data.json and contains no schema or credentials.
"""
import datetime
import decimal
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import inspect, select

from pkg import app, db


def json_value(value):
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return value


with app.app_context():
    inspector = inspect(db.engine)
    snapshot = {'database': 'vvs', 'tables': {}}
    for table_name in inspector.get_table_names():
        table = db.metadata.tables.get(table_name)
        if table is None:
            continue
        rows = db.session.execute(select(table)).mappings().all()
        snapshot['tables'][table_name] = [
            {key: json_value(value) for key, value in row.items()}
            for row in rows
        ]

    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'current_data.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as output:
        json.dump(snapshot, output, indent=2, sort_keys=True)
        output.write('\n')
    print(f'EXPORTED_TABLES={len(snapshot["tables"])}')
    print(f'OUTPUT={output_path}')