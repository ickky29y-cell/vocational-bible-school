from pkg import app, db
from pkg.models import User, Role

with app.app_context():
    role = Role.query.filter_by(name='super_admin').first()
    if not role:
        role = Role(name='super_admin', description='Super Admin')
        db.session.add(role)
        db.session.commit()
    u = User.query.filter_by(username='chaplain').first()
    if not u:
        u = User(username='chaplain', email='chaplain@example.com', role_id=role.id, is_active=True)
        u.set_password('admin1234')
        db.session.add(u)
        db.session.commit()
        print('created', u.id)
    else:
        u.set_password('admin1234')
        db.session.commit()
        print('updated', u.id)
