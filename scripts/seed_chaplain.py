from pkg import app, db
from pkg.models import User, Role
from werkzeug.security import generate_password_hash

with app.app_context():
    role = Role.query.filter_by(name='super_admin').first()
    if not role:
        role = Role(name='super_admin')
        db.session.add(role)
        db.session.commit()
    u = User.query.filter_by(username='chaplain').first()
    if not u:
        u = User(username='chaplain', email='admin@vbs.com', role_id=role.id)
        u.set_password('admin1234')
        db.session.add(u)
        db.session.commit()
        print('created chaplain')
    else:
        print('chaplain exists')
