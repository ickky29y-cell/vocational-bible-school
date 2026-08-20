from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class ClassCategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    min_age = IntegerField('Minimum Age', validators=[Optional(), NumberRange(min=0)])
    max_age = IntegerField('Maximum Age', validators=[Optional(), NumberRange(min=0)])
    assessment_method = SelectField('Assessment Method', choices=[('manual','Manual'),('cbt','CBT'),('both','Both')], validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save')
