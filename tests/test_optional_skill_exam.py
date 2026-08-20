import uuid

from pkg import app, db
from pkg.exam_paper import build_exam_questions
from pkg.models import (
    Class,
    Exam,
    ExamSection,
    ExamSectionBankRule,
    ExamAttempt,
    Question,
    QuestionBank,
    Role,
    Skill,
    StudentProfile,
    TeacherProfile,
    User,
    VbsYear,
    exam_classes,
)


def _seed_exam():
    role = Role.query.filter_by(name='teacher').first()
    if not role:
        role = Role(name='teacher')
        db.session.add(role)
        db.session.commit()

    student_role = Role.query.filter_by(name='student').first()
    if not student_role:
        student_role = Role(name='student')
        db.session.add(student_role)
        db.session.commit()

    teacher_user = User.query.filter_by(username='preview_teacher').first()
    if not teacher_user:
        teacher_user = User(username='preview_teacher', email='preview_teacher@example.com', password_hash='x', role_id=role.id, is_active=True)
        db.session.add(teacher_user)
        db.session.commit()

    teacher = TeacherProfile.query.filter_by(user_id=teacher_user.id).first()
    if not teacher:
        teacher = TeacherProfile(user_id=teacher_user.id, first_name='Preview', last_name='Teacher', phone='123')
        db.session.add(teacher)
        db.session.commit()

    year = VbsYear.query.filter_by(is_active=True).first()
    if not year:
        year = VbsYear(year=2028, theme='Optional skill', is_active=True)
        db.session.add(year)
        db.session.commit()

    cls = Class.query.filter_by(name='Preview Class', teacher_id=teacher.id, vbs_year_id=year.id).first()
    if not cls:
        cls = Class(name='Preview Class', vbs_year_id=year.id, teacher_id=teacher.id)
        db.session.add(cls)
        db.session.commit()

    suffix = uuid.uuid4().hex[:8]
    computer = Skill(name=f'Computer {suffix}', description='optional', vbs_year_id=year.id)
    catering = Skill(name=f'Catering {suffix}', description='optional', vbs_year_id=year.id)
    db.session.add_all([computer, catering])
    db.session.flush()

    common = QuestionBank(name=f'Common {suffix}', description='normal', class_id=cls.id)
    computer_bank = QuestionBank(name=f'Computer Bank {suffix}', description='skill', class_id=cls.id, skill_id=computer.id)
    catering_bank = QuestionBank(name=f'Catering Bank {suffix}', description='skill', class_id=cls.id, skill_id=catering.id)
    db.session.add_all([common, computer_bank, catering_bank])
    db.session.flush()

    for index in range(1, 6):
        db.session.add(Question(question_bank_id=common.id, question_text=f'Normal {suffix}-{index}', option_a='A', option_b='B', option_c='C', option_d='D', correct_option='A'))
    db.session.add(Question(question_bank_id=computer_bank.id, question_text=f'Computer Q {suffix}', option_a='A', option_b='B', option_c='C', option_d='D', correct_option='B'))
    db.session.add(Question(question_bank_id=catering_bank.id, question_text=f'Catering Q {suffix}', option_a='A', option_b='B', option_c='C', option_d='D', correct_option='C'))

    exam = Exam(title=f'Mixed Skill Exam {suffix}', class_id=cls.id, vbs_year_id=year.id, duration_minutes=30, skill_question_count=1, is_draft=False)
    db.session.add(exam)
    db.session.flush()
    db.session.execute(exam_classes.insert().values(exam_id=exam.id, class_id=cls.id))
    common_section = ExamSection(exam_id=exam.id, title='Common', question_bank_id=common.id, question_count=2)
    skill_section = ExamSection(exam_id=exam.id, title='Skills', question_bank_id=computer_bank.id, question_count=1)
    db.session.add_all([common_section, skill_section])
    db.session.flush()
    db.session.add(ExamSectionBankRule(exam_section_id=skill_section.id, question_bank_id=computer_bank.id, question_count=1))
    db.session.add(ExamSectionBankRule(exam_section_id=skill_section.id, question_bank_id=catering_bank.id, question_count=1))
    db.session.commit()
    return teacher_user, exam, computer, catering, common, computer_bank, catering_bank


def test_optional_skill_papers_keep_the_same_length():
    with app.app_context():
        _teacher_user, exam, computer, catering, common, computer_bank, catering_bank = _seed_exam()
        computer_paper = build_exam_questions(exam, skill_id=computer.id)
        catering_paper = build_exam_questions(exam, skill_id=catering.id)
        no_skill_paper = build_exam_questions(exam, skill_id=None)

        assert len(computer_paper) == len(catering_paper) == len(no_skill_paper) == 3
        assert computer_bank.id in {q.question_bank_id for q in computer_paper}
        assert catering_bank.id in {q.question_bank_id for q in catering_paper}
        assert computer_bank.id not in {q.question_bank_id for q in no_skill_paper}
        assert catering_bank.id not in {q.question_bank_id for q in no_skill_paper}
        assert {q.question_bank_id for q in no_skill_paper} == {common.id}


def test_teacher_preview_does_not_create_an_attempt():
    with app.app_context():
        teacher_user, exam, computer, _catering, _common, computer_bank, _catering_bank = _seed_exam()
        attempt_count = ExamAttempt.query.count()
        question_count = Question.query.count()

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['role'] = 'teacher'
                sess['useronline'] = teacher_user.id

            select_page = client.get(f'/teacher/exams/preview/{exam.id}/')
            assert select_page.status_code == 200
            assert b'Test Exam' in select_page.data

            instructions = client.get(f'/teacher/exams/preview/{exam.id}/?skill_id={computer.id}')
            assert instructions.status_code == 200
            assert b'Test Mode: This attempt will not be recorded.' in instructions.data
            assert b'Pre-Exam Instructions' in instructions.data

            run = client.post(f'/teacher/exams/preview/{exam.id}/start/')
            assert run.status_code == 200
            assert b'Question 1 of 3' in run.data
            assert computer_bank.name.encode() not in run.data
            assert ExamAttempt.query.count() == attempt_count
            assert Question.query.count() == question_count

            result = client.post(f'/teacher/exams/preview/{exam.id}/submit/', data={})
            assert result.status_code == 200
            assert b'Test Result' in result.data
            assert ExamAttempt.query.count() == attempt_count
