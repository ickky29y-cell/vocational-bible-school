#!/usr/bin/env python3
import os, sys
# ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pkg import app, db
from pkg.models import (QuestionBank, Question, Role, User, TeacherProfile, VbsYear, Class, Exam, ExamSection, ExamSectionBankRule)


def _seed_sean():
    from pkg.super_admin_routes import initialize_and_seed
    try:
        initialize_and_seed()
    except Exception:
        pass

    user = User.query.filter_by(username='sean').first()
    if not user:
        role = Role.query.filter_by(name='teacher').first()
        if not role:
            role = Role(name='teacher')
            db.session.add(role)
            db.session.commit()
        user = User(username='sean', email='sean@example.com', password_hash='x', role_id=role.id, is_active=True)
        db.session.add(user)
        db.session.commit()
    teacher = TeacherProfile.query.filter_by(user_id=user.id).first()
    if not teacher:
        teacher = TeacherProfile(user_id=user.id, first_name='Sean', last_name='Teacher', phone='123')
        db.session.add(teacher)
        db.session.commit()
    return user, teacher


with app.app_context():
    u, t = _seed_sean()
    year = VbsYear.query.filter_by(is_active=True).first()
    if not year:
        year = VbsYear(year=2027, theme='Verify', is_active=True)
        db.session.add(year)
        db.session.commit()

    class_a = Class.query.filter_by(name='V-A', vbs_year_id=year.id).first()
    if not class_a:
        class_a = Class(name='V-A', vbs_year_id=year.id, teacher_id=t.id)
        db.session.add(class_a)
        db.session.commit()
    class_b = Class.query.filter_by(name='V-B', vbs_year_id=year.id).first()
    if not class_b:
        class_b = Class(name='V-B', vbs_year_id=year.id, teacher_id=t.id)
        db.session.add(class_b)
        db.session.commit()

    bank_a = QuestionBank.query.filter_by(name='Verify A').first()
    if not bank_a:
        bank_a = QuestionBank(class_id=class_a.id, name='Verify A', description='A pool')
        db.session.add(bank_a)
        db.session.commit()
    bank_b = QuestionBank.query.filter_by(name='Verify B').first()
    if not bank_b:
        bank_b = QuestionBank(class_id=class_b.id, name='Verify B', description='B pool')
        db.session.add(bank_b)
        db.session.commit()

    # create questions
    for i in range(1,6):
        q = Question(question_bank_id=bank_a.id, question_text=f'AQ{i}', option_a='A', option_b='B', option_c='C', option_d='D', correct_option='A', difficulty='easy')
        db.session.add(q)
    for i in range(1,6):
        q = Question(question_bank_id=bank_b.id, question_text=f'BQ{i}', option_a='A', option_b='B', option_c='C', option_d='D', correct_option='B', difficulty='easy')
        db.session.add(q)
    db.session.commit()

    # create exam
    exam = Exam(title='Verify Exam', class_id=class_a.id, vbs_year_id=year.id, duration_minutes=20, is_draft=True)
    db.session.add(exam)
    db.session.commit()

    # use test client to post multi-bank section
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['role'] = 'teacher'
            sess['useronline'] = u.id

        data = {
            'action': 'add_section',
            'sec_title': 'Mixed Pool',
            'sec_description': 'mix',
            'bank_ids': [str(bank_a.id), str(bank_b.id)],
            'bank_counts': ['2','3'],
            'difficulty_filter': 'easy'
        }
        resp = client.post(f'/teacher/exams/edit/{exam.id}/', data=data, follow_redirects=False)
        print('POST status', resp.status_code)

    secs = ExamSection.query.filter_by(exam_id=exam.id).all()
    print('sections created:', len(secs))
    for s in secs:
        print('Section:', s.id, s.title, 'count', s.question_count, 'primary_bank', s.question_bank_id)
        rules = ExamSectionBankRule.query.filter_by(exam_section_id=s.id).all()
        print(' rules:', [(r.id, r.question_bank_id, r.question_count) for r in rules])

    # Also simulate generating an attempt to ensure mixed pick works
    # pick questions using the same logic as runtime
    from pkg.user_routes import student_exam_run
    # We won't call the view; instead replicate selection logic here
    selected_questions = []
    for sec in secs:
        if getattr(sec, 'bank_rules', None) and len(sec.bank_rules) > 0:
            for rule in sec.bank_rules:
                pool = Question.query.filter_by(question_bank_id=rule.question_bank_id, is_archived=False).all()
                picked = pool[:rule.question_count]
                selected_questions.extend([q.id for q in picked])
        else:
            pool = Question.query.filter_by(question_bank_id=sec.question_bank_id, is_archived=False).all()
            picked = pool[:sec.question_count]
            selected_questions.extend([q.id for q in picked])

    print('selected question ids (sampled, not randomized here):', selected_questions)

print('verification script finished')
