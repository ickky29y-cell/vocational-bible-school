import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pkg import app, db
from pkg.models import Question, QuestionBank

QUESTIONS = [
    (
        "The measurements for a gele can be which of the following?",
        "60 x 40",
        "70 x 30",
        "50 x 50",
        "All of the above",
        "D",
        "Different gele designs can use different measurements, including 60 x 40, 70 x 30, and 50 x 50; therefore all the listed measurements are possible.",
    ),
    (
        "When tying a gele, which direction should the long and short ends go?",
        "Long end down and short end up",
        "Long end up and short end down",
        "Both ends must point to the front",
        "Both ends must point to the back",
        "A",
        "A common gele tying arrangement places the longer end down and the shorter end up so the fabric can be shaped and secured.",
    ),
    (
        "Aso-oke and sego are types of gele fabric. True or false?",
        "True",
        "False",
        "Only aso-oke is a fabric",
        "Only sego is a fabric",
        "A",
        "Aso-oke and sego are both fabrics that may be used to make or style a gele.",
    ),
    (
        "Which of the following is not a type of gele style?",
        "Bridal round",
        "Rose",
        "Fan",
        "Oval",
        "D",
        "Bridal round, rose, and fan are recognized gele styles in this lesson; oval is not listed as a gele style.",
    ),
    (
        "Which item is most useful for securing a gele after it has been shaped?",
        "Hair pins",
        "Cooking spoon",
        "Notebook",
        "Water bottle",
        "A",
        "Hair pins help hold the folded and shaped gele securely in place.",
    ),
    (
        "What should a learner do before tying a gele?",
        "Arrange the fabric and make sure the wearer is comfortable",
        "Pull the fabric over the eyes",
        "Use a sharp object near the head",
        "Tie it without checking the fit",
        "A",
        "Preparing the fabric and checking comfort helps produce a neat style and keeps the wearer safe.",
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
