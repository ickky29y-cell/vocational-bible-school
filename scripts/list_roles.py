import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pkg import app
from pkg.models import Role, User

with app.app_context():
    print('Roles:')
    for r in Role.query.all():
        print(' -', r.name, '|', r.description)

    print('\nUsers:')
    for u in User.query.join(Role).all():
        print(' -', u.username, u.email, '| role=', u.role.name)
