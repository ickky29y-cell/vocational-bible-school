import time
from pkg import app, db
from pkg.models import User, Role, TeacherProfile, VbsYear, Class, StudentProfile, Exam, ExamAttempt, exam_classes
from werkzeug.security import generate_password_hash

suffix = str(int(time.time()))
with app.app_context():
    teacher_user = User.query.filter_by(username='sean').first()
    teacher = teacher_user.teacher_profile
    year = VbsYear.query.filter_by(is_active=True).first()
    cls = Class.query.filter_by(vbs_year_id=year.id, teacher_id=teacher.id).first()
    student = StudentProfile.query.filter_by(class_id=cls.id).first()
    if not student:
        print('NO_STUDENT')
        raise SystemExit(0)

    exam = Exam(title=f'Reset Control {suffix}', class_id=cls.id, vbs_year_id=year.id, duration_minutes=30, is_draft=True)
    db.session.add(exam)
    db.session.flush()
    db.session.add(ExamAttempt(student_id=student.id, exam_id=exam.id, class_id=cls.id, is_submitted=False))
    db.session.commit()
    attempt = ExamAttempt.query.filter_by(student_id=student.id, exam_id=exam.id).first()

    client = app.test_client()
    client.get('/user/logout/')
    login = client.post('/user/login/', data={'identity': 'sean', 'password': '123456'}, follow_redirects=False)
    reset = client.post(f'/teacher/exams/reset-attempt/{attempt.id}/', json={'reason': 'Live reset test'})
    print('TEACHER_LOGIN', login.status_code)
    print('RESET', reset.status_code, reset.json)
    print('ATTEMPT_AFTER_RESET', ExamAttempt.query.filter_by(id=attempt.id).first() is not None)
    assert login.status_code in (302, 303)
    assert reset.status_code == 200 and reset.json.get('success')
    assert ExamAttempt.query.filter_by(id=attempt.id).first() is None

    # Publish the temporary exam, then verify a second temporary exam is blocked.
    exam.is_draft = False
    db.session.commit()
    second = Exam(title=f'Reset Control Second {suffix}', class_id=cls.id, vbs_year_id=year.id, duration_minutes=30, is_draft=True)
    db.session.add(second)
    db.session.commit()
    conflict = client.post(f'/teacher/exams/toggle-draft/{second.id}/')
    print('ACTIVE_CONFLICT', conflict.status_code, conflict.json)
    assert conflict.status_code == 409

    db.session.delete(exam)
    db.session.delete(second)
    db.session.commit()
    print('EXAM_CONTROLS_OK')
