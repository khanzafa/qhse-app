# app/forms.py
from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, SubmitField, SelectField, TextAreaField, PasswordField, FileField
from wtforms.validators import DataRequired, IPAddress, Length, URL, EqualTo, ValidationError
from app.models import Camera, User
from app.extensions import db
from app.models import DetectorType, Weight

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
    types = SelectField('Type', coerce=int, validators=[DataRequired()])
    weights = SelectField('Weight', coerce=int, validators=[DataRequired()])
    running = BooleanField('Running')
    submit = SubmitField('Save')

class ModelForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    detector_type = SelectField('Detector Type', coerce=int, validators=[DataRequired()])
    file = FileField('File', validators=[DataRequired()])

class ContactForm(FlaskForm):
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    name = TextAreaField('Name', validators=[Length(max=100)])  # Ganti 'description' dengan 'name'
    submit = SubmitField('Save')

class OTPForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired()])
    otp = PasswordField('Password')
    submit = SubmitField('Login')

class LoginForm(FlaskForm):
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(min=8, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=64)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(min=8, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=128)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[
        ('IT', 'IT'),
        ('HR', 'HR'),
        ('Finance', 'Finance'),
        ('Accounting', 'Accounting'),
        ('Security', 'Security'),
        ('Manager', 'Manager')
    ], validators=[DataRequired()]) 
    submit = SubmitField('Register')

    def validate_phone_number(self, phone_number):
        user = User.query.filter_by(phone_number=phone_number.data).first()
        if user:
            raise ValidationError('Phone number already registered.')