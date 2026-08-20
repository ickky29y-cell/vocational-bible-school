"""Seed default roles and an initial admin user.

Run with: python scripts/seed_roles.py
"""
import sys
import os

# Ensure project root is on path when running this script directly
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pkg import app, db
from pkg.models import Role, User, TeacherProfile
from werkzeug.security import generate_password_hash

DEFAULT_ADMIN = {
    'username': 'admin',
    'email': 'admin@example.com',
    'password': 'ChangeMe123!'
}

DEFAULT_SUPER = {
    'username': 'chaplin',
    'email': 'chaplin@example.com',
    'password': 'admin1234'
}

DEFAULT_TEACHER = {
    'username': 'sean',
    'email': 'sean@vbs.com',
    'password': '123456'
}

with app.app_context():
    # Create roles (include super_admin)
    for r in ['super_admin', 'admin', 'teacher', 'student']:
        if not Role.query.filter_by(name=r).first():
            role = Role(name=r, description=f"Default {r} role")
            db.session.add(role)
    db.session.commit()

    super_role = Role.query.filter_by(name='super_admin').first()
    if not User.query.filter_by(username=DEFAULT_SUPER['username']).first():
        s = User(
            username=DEFAULT_SUPER['username'],
            email=DEFAULT_SUPER['email'],
            password_hash=generate_password_hash(DEFAULT_SUPER['password']),
            role_id=super_role.id
        )
        db.session.add(s)
        db.session.commit()
        print(f"Created super admin user: username={DEFAULT_SUPER['username']}")
    else:
        print('Super admin user already exists')

    teacher_role = Role.query.filter_by(name='teacher').first()
    if teacher_role and not User.query.filter_by(username=DEFAULT_TEACHER['username']).first():
        teacher_user = User(
            username=DEFAULT_TEACHER['username'],
            email=DEFAULT_TEACHER['email'],
            password_hash=generate_password_hash(DEFAULT_TEACHER['password']),
            role_id=teacher_role.id,
            is_active=True,
        )
        db.session.add(teacher_user)
        db.session.flush()
        if not TeacherProfile.query.filter_by(user_id=teacher_user.id).first():
            teacher_profile = TeacherProfile(user_id=teacher_user.id, first_name='Sean', last_name='Teacher', phone='08000000000')
            db.session.add(teacher_profile)
        db.session.commit()
        print(f"Created teacher user: username={DEFAULT_TEACHER['username']}")
    else:
        print('Teacher user already exists or teacher role missing')

    # Create admin user
    admin_role = Role.query.filter_by(name='admin').first()
    if not User.query.filter_by(username=DEFAULT_ADMIN['username']).first():
        u = User(
            username=DEFAULT_ADMIN['username'],
            email=DEFAULT_ADMIN['email'],
            password_hash=generate_password_hash(DEFAULT_ADMIN['password']),
            role_id=admin_role.id
        )
        db.session.add(u)
        db.session.commit()
        print('Created default admin user: username=admin')
    else:
        print('Admin user already exists')
