# guide_bot/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, MultipleFileField
from wtforms.validators import DataRequired

class DocumentForm(FlaskForm):
    files = MultipleFileField('Files', validators=[DataRequired()])
