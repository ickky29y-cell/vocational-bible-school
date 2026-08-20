import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pkg import app, db
from pkg.models import Question, QuestionBank

QUESTIONS = [
    (
        "What is one important quality of a well-tied gele?",
        "It is neat and secure",
        "It covers the eyes completely",
        "It is tied painfully tight",
        "It must be made from paper",
        "A",
        "A good gele should look neat, stay secure, and remain comfortable for the wearer.",
    ),
    (
        "Which part of the body is a gele mainly worn on?",
        "The wrist",
        "The head",
        "The ankle",
        "The shoulder",
        "B",
        "A gele is a traditional head wrap worn on the head.",
    ),
    (
        "Why should the gele fabric be folded carefully before tying it?",
        "To make the shape neat and easier to secure",
        "To make it impossible to remove",
        "To cover the wearer's face",
        "To damage the fabric",
        "A",
        "Careful folding helps the gele form a neat shape and makes it easier to secure.",
    ),
    (
        "Which behavior is safest when helping someone tie a gele?",
        "Communicate and avoid tying it too tightly",
        "Pull the fabric suddenly",
        "Use pins carelessly near the eyes",
        "Ignore whether the wearer is comfortable",
        "A",
        "Communicating and checking comfort helps prevent pain or injury while the gele is being tied.",
    ),
]

with app.app_context():
    bank = QuestionBank.query.filter_by(name="VBS Gele Skill").first()
    if not bank:
        raise SystemExit("Question bank 'VBS Gele Skill' was not found")

    existing = {q.question_text for q in Question.query.filter_by(question_bank_id=bank.id).all()}
    added = 0
    for question_text, option_a, option_b, option_c, option_d, correct, explanation in QUESTIONS:
        if question_text in existing:
            continue
        db.session.add(Question(
            question_bank_id=bank.id,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct,
            explanation=explanation,
            difficulty="medium",
            marks=2,
        ))
        added += 1

    db.session.commit()
    print(f"BANK_ID={bank.id} ADDED={added} TOTAL={Question.query.filter_by(question_bank_id=bank.id).count()}")
