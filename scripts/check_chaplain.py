from pkg import app, db
from pkg.models import User, Role

with app.app_context():
    u = User.query.filter_by(username='chaplain').first()
    if u:
        print('FOUND', u.id, u.username, u.email, u.role_id)
        r = Role.query.get(u.role_id)
        print('ROLE', r.name if r else None)
    else:
        print('NOT FOUND')
        print('ROLES:', [x.name for x in Role.query.all()])
