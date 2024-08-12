# app/forms.py
from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, IPAddress, Length, URL
from app.models import Camera

class AddCCTVForm(FlaskForm):
    location = StringField('Location', validators=[DataRequired()])    
    type = SelectField('Type', choices=[('Cabin', 'Cabin'), ('Entrance', 'Entrance'), ('Exit', 'Exit'), ('Working Area', 'Working Area')], coerce=str)
    ip_address = StringField('IP Address', validators=[URL()])        
    submit = SubmitField('Add CCTV')

class EditCCTVForm(FlaskForm):
    location = StringField('Location', validators=[DataRequired()])    
    type = SelectField('Type', choices=[('Cabin', 'Cabin'), ('Entrance', 'Entrance'), ('Exit', 'Exit'), ('Working Area', 'Working Area')], coerce=str)
    ip_address = StringField('IP Address', validators=[URL()])    
    status = SelectField('Status', choices=[('0', 'Inactive'), ('1', 'Active')], coerce=int)
    submit = SubmitField('Edit CCTV')

class SelectCCTVForm(FlaskForm):
    camera = SelectField('Select CCTV', coerce=int, validators=[DataRequired()])
    submit = SubmitField('View Feed')

class DetectorForm(FlaskForm):
    id = IntegerField('ID')
    camera_id = SelectField('Camera', coerce=int, validators=[DataRequired()])
    type = SelectField('Type', choices=[('PPE', 'PPE'), ('Gesture', 'Gesture'), ('Unfocused', 'Unfocused')], coerce=str, validators=[DataRequired()])
    running = BooleanField('Running')
    submit = SubmitField('Save')

class ContactForm(FlaskForm):
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    name = TextAreaField('Name', validators=[Length(max=100)])  # Ganti 'description' dengan 'name'
    submit = SubmitField('Save')