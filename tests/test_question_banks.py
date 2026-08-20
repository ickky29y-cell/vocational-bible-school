import uuid

from pkg import app, db
from pkg.models import QuestionBank, Role, User, TeacherProfile, VbsYear, Class, StudentProfile


def _seed_teacher_and_classes():
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

    return teacher_user, teacher, year, class_a, class_b


def test_default_teacher_seed_creates_sean_account():
    with app.app_context():
        from pkg.super_admin_routes import initialize_and_seed

        initialize_and_seed()

        user = User.query.filter_by(username='sean').first()
        assert user is not None
        assert user.role.name == 'teacher'
        assert user.check_password('123456')
        assert TeacherProfile.query.filter_by(user_id=user.id).first() is not None


def test_teacher_can_save_manual_score_without_cbt_submission():
    with app.app_context():
        teacher_user, teacher, year, class_a, class_b = _seed_teacher_and_classes()
        class_a.assessment_method = 'both'
        class_a.manual_grade_weight = 60
        class_a.cbt_grade_weight = 40
        db.session.commit()

        student_user = User.query.filter_by(username='manual_score_student').first()
        if not student_user:
            student_user = User(username='manual_score_student', email='manual_score_student@example.com', password_hash='x', role_id=Role.query.filter_by(name='student').first().id, is_active=True)
            db.session.add(student_user)
            db.session.commit()

        student = StudentProfile.query.filter_by(user_id=student_user.id, class_id=class_a.id).first()
        if not student:
            student = StudentProfile(user_id=student_user.id, first_name='Manual', last_name='Student', age=8, gender='male', class_id=class_a.id, vbs_year_id=year.id)
            db.session.add(student)
            db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['role'] = 'teacher'
                sess['useronline'] = teacher_user.id

            response = client.post('/teacher/assessment/', data={
                'action': 'save_manual_score',
                'class_id': str(class_a.id),
                'student_id': str(student.id),
                'manual_score': '85',
                'manual_comment': 'Strong effort'
            }, follow_redirects=False)
            assert response.status_code in (302, 303)

            page = client.get(f'/teacher/assessment/?class_id={class_a.id}')
            assert page.status_code == 200
            assert b'85' in page.data
            assert b'Pending' in page.data


def test_question_banks_support_multiple_classes():
    with app.app_context():
        teacher_user, teacher, year, class_a, class_b = _seed_teacher_and_classes()
        assert hasattr(QuestionBank, 'assigned_classes')
        assert 'question_bank_classes' in db.metadata.tables

        unique_suffix = uuid.uuid4().hex[:8]
        bank_name = f'Shared Bank {unique_suffix}'

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['role'] = 'teacher'
                sess['useronline'] = teacher_user.id

            bank_response = client.post('/teacher/question-banks/', data={
                'name': bank_name,
                'description': 'Shared class bank',
                'class_ids': [str(class_a.id), str(class_b.id)]
            }, follow_redirects=False)
            assert bank_response.status_code in (302, 303)

            bank = QuestionBank.query.filter_by(name=bank_name).first()
            assert bank is not None
            assert bank.class_id == class_a.id
            assert {c.id for c in bank.assigned_classes} == {class_b.id}

            edit_response = client.post(f'/teacher/question-banks/{bank.id}/edit/', data={
                'class_ids': [str(class_a.id), str(class_b.id)]
            }, follow_redirects=False)
            assert edit_response.status_code in (302, 303)

            bank = QuestionBank.query.get(bank.id)
            selected = {bank.class_id} | {c.id for c in bank.assigned_classes}
            assert selected == {class_a.id, class_b.id}


def test_exam_sections_can_use_multiple_banks_with_per_bank_counts():
    with app.app_context():
        from pkg.models import Exam, ExamSection, Question

        teacher_user, teacher, year, class_a, class_b = _seed_teacher_and_classes()
        bank_a = QuestionBank.query.filter_by(name='Alpha Bank').first()
        if not bank_a:
            bank_a = QuestionBank(class_id=class_a.id, name='Alpha Bank', description='Alpha pool')
            db.session.add(bank_a)
            db.session.commit()

        bank_b = QuestionBank.query.filter_by(name='Beta Bank').first()
        if not bank_b:
            bank_b = QuestionBank(class_id=class_b.id, name='Beta Bank', description='Beta pool')
            db.session.add(bank_b)
            db.session.commit()

        for idx in range(1, 6):
            db.session.add(Question(question_bank_id=bank_a.id, question_text=f'AQ {idx}', option_a='A', option_b='B', option_c='C', option_d='D', correct_option='A', difficulty='easy'))
        for idx in range(1, 6):
            db.session.add(Question(question_bank_id=bank_b.id, question_text=f'BQ {idx}', option_a='A', option_b='B', option_c='C', option_d='D', correct_option='B', difficulty='easy'))
        db.session.commit()

        exam = Exam(title='Multi Bank Quiz', class_id=class_a.id, vbs_year_id=year.id, duration_minutes=30, is_draft=True)
        db.session.add(exam)
        db.session.flush()

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['role'] = 'teacher'
                sess['useronline'] = teacher_user.id

            response = client.post(f'/teacher/exams/edit/{exam.id}/', data={
                'action': 'add_section',
                'sec_title': 'Mixed Pool',
                'sec_description': 'Diverse section',
                'bank_ids': [str(bank_a.id), str(bank_b.id)],
                'bank_counts': ['2', '3'],
                'difficulty_filter': 'easy'
            }, follow_redirects=False)
            assert response.status_code in (302, 303)

        section = ExamSection.query.filter_by(exam_id=exam.id).first()
        assert section is not None
        assert section.question_count == 5
        assert len(section.bank_rules) == 2
        assert {link.question_bank_id for link in section.bank_rules} == {bank_a.id, bank_b.id}
        assert sum(link.question_count for link in section.bank_rules) == 5


def test_question_bank_form_shows_all_teacher_classes_even_manual_classes():
    with app.app_context():
        teacher_user, teacher, year, class_a, class_b = _seed_teacher_and_classes()
        class_a.assessment_method = 'manual'
        class_b.assessment_method = 'manual'
        db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['role'] = 'teacher'
                sess['useronline'] = teacher_user.id

            response = client.get('/teacher/question-banks/')
            assert response.status_code == 200
            assert class_a.name.encode() in response.data
            assert class_b.name.encode() in response.data


def test_question_bank_page_works_when_superadmin_view_as_teacher():
    with app.app_context():
        teacher_user, teacher, year, class_a, class_b = _seed_teacher_and_classes()
        role = Role.query.filter_by(name='super_admin').first()
        if not role:
            role = Role(name='super_admin')
            db.session.add(role)
            db.session.commit()

        admin_user = User.query.filter_by(username='super_admin_viewtest').first()
        if not admin_user:
            admin_user = User(username='super_admin_viewtest', email='super_admin_viewtest@example.com', password_hash='x', role_id=role.id, is_active=True)
            db.session.add(admin_user)
            db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['role'] = 'super_admin'
                sess['useronline'] = admin_user.id
                sess['view_as_teacher'] = teacher.id

            response = client.get('/teacher/question-banks/')
            assert response.status_code == 200
            assert class_a.name.encode() in response.data
            assert class_b.name.encode() in response.data


def test_manage_students_page_loads_for_assigned_classes():
    with app.app_context():
        teacher_user, teacher, year, class_a, class_b = _seed_teacher_and_classes()

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['role'] = 'teacher'
                sess['useronline'] = teacher_user.id

            response = client.get('/teacher/students/')
            assert response.status_code == 200
            assert class_a.name.encode() in response.data
            assert class_b.name.encode() in response.data
            assert b'No classes assigned to you yet.' not in response.data


def test_teacher_can_edit_class_grade_weights_for_each_class():
    with app.app_context():
        teacher_user, teacher, year, class_a, class_b = _seed_teacher_and_classes()

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['role'] = 'teacher'
                sess['useronline'] = teacher_user.id

            response = client.post('/teacher/assessment/', data={
                'action': 'save_weights',
                'class_id': str(class_a.id),
                'manual_grade_weight': '55',
                'cbt_grade_weight': '45'
            }, follow_redirects=False)
            assert response.status_code in (302, 303)

            db.session.refresh(class_a)
            assert class_a.manual_grade_weight == 55
            assert class_a.cbt_grade_weight == 45

            page = client.get(f'/teacher/assessment/?class_id={class_a.id}')
            assert page.status_code == 200
            assert b'55' in page.data
            assert b'45' in page.data


def test_teacher_can_set_assessment_method_and_pending_cbt_status():
    with app.app_context():
        teacher_user, teacher, year, class_a, class_b = _seed_teacher_and_classes()

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['role'] = 'teacher'
                sess['useronline'] = teacher_user.id

            response = client.post('/teacher/assessment/', data={
                'action': 'save_weights',
                'class_id': str(class_a.id),
                'manual_grade_weight': '60',
                'cbt_grade_weight': '40',
                'assessment_method': 'both'
            }, follow_redirects=False)
            assert response.status_code in (302, 303)

            db.session.refresh(class_a)
            assert class_a.assessment_method == 'both'

            page = client.get(f'/teacher/assessment/?class_id={class_a.id}')
            assert page.status_code == 200
            assert b'Assessment Mode' in page.data
            assert b'Both' in page.data
