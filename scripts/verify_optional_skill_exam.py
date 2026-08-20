import time
from pkg import app, db
from pkg.models import User, Role, TeacherProfile, VbsYear, Class, Skill, StudentProfile, QuestionBank, Question, Exam, ExamSection, ExamSectionBankRule, ExamAttempt, AttemptQuestion, exam_classes
from werkzeug.security import generate_password_hash

suffix = str(int(time.time()))

with app.app_context():
    year = VbsYear.query.filter_by(is_active=True).first()
    teacher_user = User.query.filter_by(username='sean').first()
    teacher = teacher_user.teacher_profile if teacher_user else TeacherProfile.query.first()
    if not year or not teacher:
        print('MISSING_ACTIVE_YEAR_OR_TEACHER')
        raise SystemExit(0)
    cls = Class.query.filter_by(vbs_year_id=year.id, teacher_id=teacher.id).first()
    if not cls:
        print('MISSING_TEACHER_CLASS')
        raise SystemExit(0)
    role = Role.query.filter_by(name='student').first()
    skill = Skill(name=f'Computer Test {suffix}', description='preview skill', vbs_year_id=year.id)
    db.session.add(skill)
    db.session.flush()

    common = QuestionBank(name=f'Common Test {suffix}', description='common', class_id=cls.id)
    skilled = QuestionBank(name=f'Skill Test {suffix}', description='skill', class_id=cls.id, skill_id=skill.id)
    db.session.add_all([common, skilled])
    db.session.flush()
    for index in range(1, 5):
        db.session.add(Question(question_bank_id=common.id, question_text=f'Common {suffix}-{index}', option_a='A', option_b='B', option_c='C', option_d='D', correct_option='A'))
    for index in range(1, 3):
        db.session.add(Question(question_bank_id=skilled.id, question_text=f'Skill {suffix}-{index}', option_a='A', option_b='B', option_c='C', option_d='D', correct_option='B'))

    exam = Exam(title=f'Optional Skill Test {suffix}', class_id=cls.id, vbs_year_id=year.id, duration_minutes=30, skill_question_count=1, is_draft=False)
    db.session.add(exam)
    db.session.flush()
    db.session.execute(exam_classes.insert().values(exam_id=exam.id, class_id=cls.id))
    common_section = ExamSection(exam_id=exam.id, title='Common', question_bank_id=common.id, question_count=2)
    skill_section = ExamSection(exam_id=exam.id, title='Optional Skills', question_bank_id=skilled.id, question_count=1)
    db.session.add_all([common_section, skill_section])
    db.session.flush()
    db.session.add(ExamSectionBankRule(exam_section_id=skill_section.id, question_bank_id=skilled.id, question_count=1))

    def make_student(label, assigned_skill):
        user = User(username=f'skill_{label}_{suffix}', email=f'skill_{label}_{suffix}@example.com', password_hash=generate_password_hash('testpass'), role_id=role.id)
        db.session.add(user)
        db.session.flush()
        student = StudentProfile(user_id=user.id, first_name=label, last_name='Test', age=10, gender='Other', class_id=cls.id, skill_id=assigned_skill.id if assigned_skill else None, vbs_year_id=year.id)
        db.session.add(student)
        db.session.flush()
        return user, student

    skilled_user, skilled_student = make_student('Skilled', skill)
    plain_user, plain_student = make_student('Plain', None)
    db.session.commit()

    def run_student(user, student):
        client = app.test_client()
        client.get('/user/logout/')
        login = client.post('/user/login/', data={'identity': user.username, 'password': 'testpass'}, follow_redirects=False)
        print('LOGIN', user.username, login.status_code, login.headers.get('Location'))
        assert login.status_code in (302, 303), login.status_code
        start = client.post(f'/student/exam/prestart/{exam.id}/', data={'selfie_image': 'skipped'}, follow_redirects=False)
        print('START', user.username, start.status_code, start.headers.get('Location'))
        assert start.status_code in (302, 303), start.status_code
        attempt = ExamAttempt.query.filter_by(student_id=student.id, exam_id=exam.id).first()
        page = client.get(f'/student/exam/run/{attempt.id}/')
        assert page.status_code == 200, page.status_code
        rows = AttemptQuestion.query.filter_by(attempt_id=attempt.id).all()
        bank_ids = [row.question.question_bank_id for row in rows]
        return len(rows), bank_ids

    skilled_count, skilled_banks = run_student(skilled_user, skilled_student)
    plain_count, plain_banks = run_student(plain_user, plain_student)
    print('SKILLED', skilled_count, skilled_banks)
    print('NO_SKILL', plain_count, plain_banks)
    assert skilled_count == plain_count == 3
    assert skilled.id in skilled_banks
    assert skilled.id not in plain_banks

    teacher_user = teacher.user
    teacher_client = app.test_client()
    teacher_client.get('/user/logout/')
    teacher_login = teacher_client.post('/user/login/', data={'identity': teacher_user.username, 'password': '123456'}, follow_redirects=False)
    print('TEACHER_LOGIN', teacher_login.status_code, teacher_login.headers.get('Location'))
    with teacher_client.session_transaction() as sess:
        print('TEACHER_SESSION', dict(sess))
    assert teacher_login.status_code in (302, 303), teacher_login.status_code
    print('TEACHER_DASHBOARD', teacher_client.get('/teacher/dashboard/', follow_redirects=False).status_code)
    preview_select = teacher_client.get(f'/teacher/exams/preview/{exam.id}/')
    assert preview_select.status_code == 200, preview_select.status_code
    assert b'Test Mode: This attempt will not be recorded.' in preview_select.data
    assert b'Student without a skill' in preview_select.data

    preview = teacher_client.get(f'/teacher/exams/preview/{exam.id}/?skill_id={skill.id}')
    no_skill_preview = teacher_client.get(f'/teacher/exams/preview/{exam.id}/?no_skill=1')
    print('PREVIEW_INSTRUCTIONS', preview.status_code, no_skill_preview.status_code)
    assert preview.status_code == 200, preview.status_code
    assert no_skill_preview.status_code == 200, no_skill_preview.status_code
    assert b'Test Mode' in preview.data
    assert b'Pre-Exam Instructions' in preview.data
    assert b'Face Verification' not in preview.data or b'display:none' in preview.data

    attempt_count_before = ExamAttempt.query.count()
    question_count_before = Question.query.count()
    start = teacher_client.post(f'/teacher/exams/preview/{exam.id}/start/', follow_redirects=False)
    assert start.status_code == 200, start.status_code
    assert b'Test Mode: This attempt will not be recorded.' in start.data
    assert b'Question 1 of' in start.data
    assert ExamAttempt.query.count() == attempt_count_before
    assert Question.query.count() == question_count_before

    preview_submit = teacher_client.post(f'/teacher/exams/preview/{exam.id}/submit/', data={}, follow_redirects=False)
    assert preview_submit.status_code == 200, preview_submit.status_code
    assert b'Test Result' in preview_submit.data
    assert ExamAttempt.query.count() == attempt_count_before
    for path in ('/teacher/skills/', '/teacher/students/', '/teacher/question-banks/', '/teacher/exams/'):
        page = teacher_client.get(path)
        assert page.status_code == 200, (path, page.status_code)
        print('TEACHER_PAGE', path, page.status_code)
    print('PREVIEW_SKILL', preview.status_code)
    print('PREVIEW_NO_SKILL', no_skill_preview.status_code)
    print('PREVIEW_SUBMIT', preview_submit.status_code)
    print('OPTIONAL_SKILL_FLOW_OK')
