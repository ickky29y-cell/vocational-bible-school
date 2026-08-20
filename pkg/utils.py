from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user, login_required
from flask import session
from pkg.models import Class, teacher_classes, TeacherProfile
from pkg import db


def role_required(role_name):
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            try:
                if not current_user.is_authenticated:
                    flash('Please login first', 'errormsg')
                    return redirect(url_for('user_login'))
                if current_user.role is None or current_user.role.name != role_name:
                    flash('Unauthorized access', 'errormsg')
                    return redirect(url_for('home_page'))
            except Exception:
                flash('Unauthorized access', 'errormsg')
                return redirect(url_for('home_page'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def admin_required(f):
    return role_required('admin')(f)


def current_user_id():
    try:
        if current_user and getattr(current_user, 'is_authenticated', False):
            return current_user.id
    except Exception:
        pass
    return session.get('useronline')


def current_role_name():
    try:
        if current_user and getattr(current_user, 'is_authenticated', False) and current_user.role:
            return current_user.role.name
    except Exception:
        pass
    return session.get('role')


def get_teacher_classes(teacher_id, vbs_year_id=None):
    # Return classes where teacher is primary or assigned via teacher_classes
    q = db.session.query(Class).distinct()
    if vbs_year_id:
        q = q.filter(Class.vbs_year_id == vbs_year_id)
    # primary teacher
    primary = q.filter(Class.teacher_id == teacher_id)
    # assigned via association
    assigned = db.session.query(Class).join(teacher_classes, Class.id == teacher_classes.c.class_id).filter(teacher_classes.c.teacher_id == teacher_id)
    # union
    classes = primary.union(assigned).all()
    return classes


def teacher_has_access_to_class(teacher_id, class_id):
    c = Class.query.get(class_id)
    if not c:
        return False
    if c.teacher_id == teacher_id:
        return True
    # check association
    res = db.session.query(teacher_classes).filter_by(teacher_id=teacher_id, class_id=class_id).first()
    return bool(res)


def set_active_class(class_id):
    session['active_class'] = class_id


def get_active_class():
    return session.get('active_class')


def get_effective_teacher_profile():
    """Return TeacherProfile for the active teacher or the impersonated teacher."""
    from pkg.models import TeacherProfile

    try:
        imp_id = session.get('view_as_teacher')
        if imp_id:
            teacher = TeacherProfile.query.get(imp_id)
            if teacher:
                return teacher
    except Exception:
        pass

    try:
        if current_user and getattr(current_user, 'is_authenticated', False):
            if getattr(getattr(current_user, 'role', None), 'name', None) == 'teacher':
                return TeacherProfile.query.filter_by(user_id=current_user.id).first()
    except Exception:
        pass

    uid = session.get('useronline')
    if uid:
        role_name = (session.get('role') or '').lower()
        if role_name == 'teacher':
            return TeacherProfile.query.filter_by(user_id=uid).first()

    return None
