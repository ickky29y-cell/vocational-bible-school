import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pkg import app, db
from pkg.models import Question, QuestionBank

QUESTIONS = [
    ("What is HTML mainly used for?", "Creating the structure of web pages", "Editing videos", "Creating databases", "Protecting computers from viruses", "A", "HTML defines the structure and content of web pages."),
    ("Which tag is used to create the largest heading in HTML?", "<heading>", "<h6>", "<h1>", "<head>", "C", "The h1 element represents the highest-level HTML heading."),
    ("Which tag is used to create a paragraph?", "<paragraph>", "<p>", "<text>", "<para>", "B", "The p element marks a paragraph of text."),
    ("Which tag is used to create a link?", "<link>", "<a>", "<url>", "<href>", "B", "The a element creates a hyperlink; its href attribute supplies the destination."),
    ("Which tag is used to display an image?", "<image>", "<img>", "<pic>", "<src>", "B", "The img element embeds an image, usually using src for its file location."),
    ("Which tag is commonly used to make text italic?", "<italic>", "<i>", "<it>", "<style>", "B", "The i element commonly renders text in an italic style."),
    ("Which tag is used for each item in a list?", "<item>", "<li>", "<list>", "<ul>", "B", "The li element represents an individual list item."),
    ("Which HTML tag is used to create a button?", "<click>", "<button>", "<btn>", "<inputbutton>", "B", "The button element creates a clickable button control."),
    ("Which tag is used to create a text input field?", "<text>", "<input>", "<textbox>", "<field>", "B", "The input element creates form controls; type=\"text\" creates a text field."),
    ("Which HTML attribute can be used to add CSS directly to an element?", "design", "css", "style", "color", "C", "The style attribute contains inline CSS declarations for an individual element."),
    ("Which CSS property is used to change the background color?", "background-color", "bg-color", "color-background", "back-color", "A", "The background-color property sets an element's background color."),
    ("Which CSS property can be used to make an element taller?", "height", "tall", "size-height", "length", "A", "The height property controls the height of an element's content area."),
]

with app.app_context():
    bank = QuestionBank.query.filter_by(name="VBS computer skill").first()
    if not bank:
        raise SystemExit("Question bank 'VBS computer skill' was not found")

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
