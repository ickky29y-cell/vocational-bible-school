from pkg import app
from pkg.models import Class

with app.app_context():
    cls = Class.query.first()
    print('CLASS', cls.name if cls else None)
    print('TEACHER', cls.teacher.user.username if cls and cls.teacher else None)
