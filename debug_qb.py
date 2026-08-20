from pkg import app, db
from pkg.models import QuestionBank, Role, User, TeacherProfile, VbsYear, Class

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

    print('teacher', teacher_user.id, teacher.id, class_a.id, class_b.id)
    print('classes for teacher', [c.id for c in db.session.query(Class).all()])

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['role'] = 'teacher'
            sess['useronline'] = teacher_user.id

        resp = client.post('/teacher/question-banks/', data={
            'name': 'Shared Bank X',
            'description': 'Shared class bank',
            'class_ids': [str(class_a.id), str(class_b.id)]
        }, follow_redirects=True)

        print('status', resp.status_code)
        print(resp.get_data(as_text=True)[:2000])
        print('banks after', QuestionBank.query.all())
