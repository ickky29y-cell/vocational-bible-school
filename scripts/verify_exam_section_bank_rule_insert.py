from pkg import app, db
from pkg.models import ExamSection, QuestionBank, ExamSectionBankRule

with app.app_context():
    section = ExamSection.query.first()
    bank = QuestionBank.query.first()
    if not section or not bank:
        print('MISSING_TEST_REFERENCES')
        raise SystemExit(0)

    rule = ExamSectionBankRule(
        exam_section_id=section.id,
        question_bank_id=bank.id,
        question_count=1,
    )
    db.session.add(rule)
    db.session.flush()
    print('GENERATED_ID', rule.id)
    db.session.rollback()
