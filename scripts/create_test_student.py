from pkg import app, db
from pkg.models import User, Role, TeacherProfile, Class, VbsYear, StudentProfile
import random

with app.app_context():
    # Ensure teacher exists
    teacher_user = User.query.filter_by(username='sean').first()
    if not teacher_user:
        print('teacher not found')
        raise SystemExit(1)
    teacher = TeacherProfile.query.filter_by(user_id=teacher_user.id).first()
    if not teacher:
        print('teacher profile missing')
        raise SystemExit(1)

    active_year = VbsYear.query.filter_by(is_active=True).first()
    if not active_year:
        active_year = VbsYear(year=2027, theme='Auto', is_active=True)
        db.session.add(active_year)
        db.session.commit()

    # Find or create a class assigned to the teacher
    cls = Class.query.filter_by(teacher_id=teacher.id, vbs_year_id=active_year.id).first()
    if not cls:
        cls = Class(name='Auto Test Class', vbs_year_id=active_year.id, teacher_id=teacher.id, min_age=5, max_age=8)
        db.session.add(cls)
        db.session.commit()

    # Create a student user
    role = Role.query.filter_by(name='student').first()
    if not role:
        role = Role(name='student', description='VBS Pupil')
        db.session.add(role)
        db.session.commit()

    uname = f'test_student_{random.randint(1000,9999)}'
    pwd = 'studentpwd'
    user = User(username=uname, email=f'{uname}@example.com', role_id=role.id)
    user.set_password(pwd)
    db.session.add(user)
    db.session.flush()

    student = StudentProfile(user_id=user.id, first_name='Auto', last_name='Student', age=5, gender='Male', class_id=cls.id, vbs_year_id=active_year.id)
    db.session.add(student)
    db.session.commit()

    print('created', student.id, user.username, pwd, 'class', cls.id)
