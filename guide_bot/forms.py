# guide_bot/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, MultipleFileField, SelectMultipleField
from wtforms.validators import DataRequired

class DocumentFileForm(FlaskForm):
    files = MultipleFileField('Files', validators=[DataRequired()], render_kw={'webkitdirectory':False})
    allowed_roles = SelectMultipleField('Allowed Roles', choices=[
        ('IT', 'IT'),
        ('HR', 'HR'),
        ('Finance', 'Finance'),
        ('Accounting', 'Accounting'),
        ('Security', 'Security')
    ])

class DocumentFolderForm(FlaskForm):
    files = MultipleFileField('Files', validators=[DataRequired()], render_kw={'webkitdirectory':True})
    allowed_roles = SelectMultipleField('Allowed Roles', choices=[
        ('IT', 'IT'),
        ('HR', 'HR'),
        ('Finance', 'Finance'),
        ('Accounting', 'Accounting'),
        ('Security', 'Security')
    ])

class NewFolderForm(FlaskForm):
    folder_name = StringField('Folder Name', validators=[DataRequired()])

class EditFileForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    file = FileField('File', validators=[DataRequired()])
    allowed_roles = SelectMultipleField('Allowed Roles', choices=[
        ('IT', 'IT'),
        ('HR', 'HR'),
        ('Finance', 'Finance'),
        ('Accounting', 'Accounting'),
        ('Security', 'Security')
    ])