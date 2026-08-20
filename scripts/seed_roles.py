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
from pkg.models import Role, User
from werkzeug.security import generate_password_hash

DEFAULT_SUPER = {
    'username': 'chaplain',
    'email': 'admin@vbs.com',
    'password': 'admin1234'
}

with app.app_context():
    # Create roles (include super_admin)
    for r in ['super_admin', 'student']:
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

