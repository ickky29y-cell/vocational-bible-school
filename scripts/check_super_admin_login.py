from pkg import app, db
from pkg.models import User

with app.app_context():
    user = User.query.filter_by(username='chaplain').first()
    print('EXISTS', bool(user))
    print('ROLE', user.role.name if user and user.role else None)
    print('PASSWORD_OK', user.check_password('admin1234') if user else None)
