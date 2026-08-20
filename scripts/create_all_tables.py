import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pkg import db, app

with app.app_context():
    print('Creating all tables from models...')
    db.create_all()
    print('Done creating tables.')
