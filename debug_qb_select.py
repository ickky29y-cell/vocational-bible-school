from pkg import app, db
from pkg.models import Role, User, TeacherProfile, VbsYear, Class
from pkg.utils import get_teacher_classes

with app.app_context():
    role = Role.query.filter_by(name='teacher').first()
    if not role:
        role = Role(name='teacher')
        db.session.add(role)
        db.session.commit()
    teacher_user = User.query.filter_by(username='qb_teacher').first()
    if not teacher_user:
        teacher_user = User(username='qb_teacher', email='qb_teacher@example.com', password_hash='x', role_id=role.id, is_active=True)
        db.session.add(teacher_user)
        db.session.commit()
    teacher = TeacherProfile.query.filter_by(user_id=teacher_user.id).first()
    if not teacher:
        teacher = TeacherProfile(user_id=teacher_user.id, first_name='QB', last_name='Teacher', phone='123')
        db.session.add(teacher)
        db.session.commit()
    year = VbsYear.query.filter_by(year=2027).first()
    if not year:
        year = VbsYear(year=2027, theme='Multi class test', is_active=True)
        db.session.add(year)
        db.session.commit()
    class_a = Class.query.filter_by(name='Alpha Class', vbs_year_id=year.id).first()
    if not class_a:
        class_a = Class(name='Alpha Class', vbs_year_id=year.id, teacher_id=teacher.id)
        db.session.add(class_a)
        db.session.commit()
    class_b = Class.query.filter_by(name='Beta Class', vbs_year_id=year.id).first()
    if not class_b:
        class_b = Class(name='Beta Class', vbs_year_id=year.id, teacher_id=teacher.id)
        db.session.add(class_b)
        db.session.commit()

    classes = get_teacher_classes(teacher.id, year.id)
    class_ids = [c.id for c in classes]
    print('class_ids', class_ids)

    with app.test_request_context('/teacher/question-banks/', method='POST', data={'name': 'Shared Bank Z', 'description': 'Shared class bank', 'class_ids': [str(class_a.id), str(class_b.id)]}):
        class_ids_selected = request = None
        from flask import request
        class_ids_selected = request.form.getlist('class_ids')
        print('raw', class_ids_selected)
        selected_classes = []
        for cls_id in class_ids_selected:
            try:
                cid = int(cls_id)
                print('try cid', cid, 'allowed', cid in class_ids)
                if cid not in class_ids:
                    continue
                selected_classes.append(cid)
            except (TypeError, ValueError):
                print('bad value', cls_id)
                continue
        print('selected_classes', selected_classes)
