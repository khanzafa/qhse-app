# guide_bot/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, MultipleFileField
from wtforms.validators import DataRequired

class DocumentFileForm(FlaskForm):
    files = MultipleFileField('Files', validators=[DataRequired()], render_kw={'webkitdirectory':False})

class DocumentFolderForm(FlaskForm):
    files = MultipleFileField('Files', validators=[DataRequired()], render_kw={'webkitdirectory':True})
