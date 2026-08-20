import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pkg import app
from pkg.models import Role, User

with app.app_context():
    roles = Role.query.all()
    print('Roles:')
    for r in roles:
        print(' -', r.id, r.name, r.description)

    admin = User.query.filter_by(username='admin').first()
    print('\nAdmin user:')
    if admin:
        print(' -', admin.id, admin.username, admin.email, 'role_id=', admin.role_id)
    else:
        print(' - not found')
