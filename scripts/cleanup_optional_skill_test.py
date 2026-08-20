from pkg import app, db
from pkg.models import User, StudentProfile, ExamAttempt, AttemptQuestion, Exam, ExamSectionBankRule, ExamSection, Question, QuestionBank, Skill
from pkg.models import exam_classes, question_bank_classes
from sqlalchemy import delete

with app.app_context():
    exams = Exam.query.filter(Exam.title.like('Optional Skill Test %')).all()
    exam_ids = [exam.id for exam in exams]
    attempts = ExamAttempt.query.filter(ExamAttempt.exam_id.in_(exam_ids)).all() if exam_ids else []
    attempt_ids = [attempt.id for attempt in attempts]
    if attempt_ids:
        db.session.execute(delete(AttemptQuestion).where(AttemptQuestion.attempt_id.in_(attempt_ids)))
        db.session.execute(delete(ExamAttempt).where(ExamAttempt.id.in_(attempt_ids)))
    if exam_ids:
        section_ids = [section.id for section in ExamSection.query.filter(ExamSection.exam_id.in_(exam_ids)).all()]
        if section_ids:
            db.session.execute(delete(ExamSectionBankRule).where(ExamSectionBankRule.exam_section_id.in_(section_ids)))
            db.session.execute(delete(ExamSection).where(ExamSection.id.in_(section_ids)))
        db.session.execute(delete(exam_classes).where(exam_classes.c.exam_id.in_(exam_ids)))
        db.session.execute(delete(Exam).where(Exam.id.in_(exam_ids)))

    banks = QuestionBank.query.filter(QuestionBank.name.like('Common Test %') | QuestionBank.name.like('Skill Test %')).all()
    bank_ids = [bank.id for bank in banks]
    if bank_ids:
        db.session.execute(delete(Question).where(Question.question_bank_id.in_(bank_ids)))
        db.session.execute(delete(question_bank_classes).where(question_bank_classes.c.question_bank_id.in_(bank_ids)))
        db.session.execute(delete(QuestionBank).where(QuestionBank.id.in_(bank_ids)))

    skills = Skill.query.filter(Skill.name.like('Computer Test %')).all()
    skill_ids = [skill.id for skill in skills]
    if skill_ids:
        db.session.execute(delete(StudentProfile).where(StudentProfile.skill_id.in_(skill_ids)))
        db.session.execute(delete(Skill).where(Skill.id.in_(skill_ids)))

    users = User.query.filter(User.username.like('skill_%')).all()
    for user in users:
        if user.student_profile:
            db.session.delete(user.student_profile)
        db.session.delete(user)
    sean = User.query.filter_by(username='sean').first()
    if sean:
        sean.set_password('123456')
    db.session.commit()
    print('CLEANED', len(exams), 'exams,', len(users), 'users')
