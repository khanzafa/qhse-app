# app/forms.py
from flask_login import current_user
from flask_wtf import FlaskForm
from flask import session
from wtforms import BooleanField, IntegerField, SelectMultipleField, StringField, SubmitField, SelectField, TextAreaField, PasswordField, FileField, widgets
from wtforms.validators import DataRequired, IPAddress, Length, URL, EqualTo, ValidationError
from app.models import CCTV, Contact, Detector, MessageTemplate, Permission, User
from app.extensions import db
from app.models import DetectorType, Weight
from utils.auth import get_allowed_permission_ids

class AddCCTVForm(FlaskForm):
    location = StringField('Location', validators=[DataRequired()], 
                           render_kw={"placeholder": "Location tidak boleh duplicate"})    
    type = SelectField('Type', choices=[('Cabin', 'Cabin'), ('Entrance', 'Entrance'), ('Exit', 'Exit'), ('Working Area', 'Working Area')], coerce=str)
    ip_address = StringField('IP Address', validators=[URL(allow_ip=True)])        
    submit = SubmitField('Add CCTV')

class EditCCTVForm(FlaskForm):
    location = StringField('Location', validators=[DataRequired()])    
    type = SelectField('Type', choices=[('Cabin', 'Cabin'), ('Entrance', 'Entrance'), ('Exit', 'Exit'), ('Working Area', 'Working Area')], coerce=str)
    ip_address = StringField('IP Address', validators=[URL()])    
    status = SelectField('Status', choices=[('0', 'Inactive'), ('1', 'Active')], coerce=int)
    submit = SubmitField('Edit CCTV')

class CCTVForm(FlaskForm):
    location = StringField('Location', validators=[DataRequired()])    
    type = StringField('Type')
    ip_address = StringField('IP Address', validators=[DataRequired()])    
    status = SelectField('Status', choices=[('0', 'Inactive'), ('1', 'Active')], coerce=int, default=1)
    submit = SubmitField('Save')

class SelectCCTVForm(FlaskForm):
    cctv = SelectField('Select CCTV', coerce=int, validators=[DataRequired()])
    submit = SubmitField('View Feed')

class DetectorForm(FlaskForm):
    id = IntegerField('ID')
    cctv_id = SelectField('CCTV', coerce=int, validators=[DataRequired()])    
    weight_id = SelectField('Weight', coerce=int, validators=[DataRequired()])
    running = BooleanField('Running', default=False)
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cctv_id.choices = [(cctv.id, cctv.location) for cctv in CCTV.query.filter(CCTV.permission_id == session.get('permission_id')).all()]
        self.weight_id.choices = [(weight.id, weight.name) for weight in Weight.query.filter(Weight.permission_id == session.get('permission_id')).all()]
        

class ModelForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    detector_type = SelectField('Detector Type', coerce=int, validators=[DataRequired()])
    file = FileField('File', validators=[DataRequired()])
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detector_type.choices = [(detector_type.id, detector_type.name) for detector_type in DetectorType.query.all()]

class ContactForm(FlaskForm):
    phone_number = StringField('Phone', validators=[Length(max=64)])
    name = StringField('Name', validators=[Length(max=30)])
    description = TextAreaField('Description', validators=[Length(max=100)])
    submit = SubmitField('Save')

class MessageTemplateForm(FlaskForm):
    name = StringField('Name', validators=[Length(max=30)])
    template = TextAreaField('Template', validators=[Length(max=4096)])

class NotificationRuleForm(FlaskForm):
    detector_id = SelectField('Detector', coerce=int, validators=[DataRequired()])
    contact_id = SelectField('Contact', coerce=int, validators=[DataRequired()])
    message_template_id = SelectField('Message Template', coerce=int, validators=[DataRequired()])
    
    submit = SubmitField('Save')

    def __init__(self, session_role=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detector_id.choices = [(detector.id, detector.id) for detector in Detector.query.filter(Detector.permission_id == session.get('permission_id')).all()]
        self.contact_id.choices = [(contact.id, contact.name) for contact in Contact.query.filter(Contact.permission_id == session.get('permission_id')).all()]
        self.message_template_id.choices = [(template.id, template.name) for template in MessageTemplate.query.filter(MessageTemplate.permission_id == session.get('permission_id')).all()]
        

class OTPForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired()])
    otp = PasswordField('Password')
    submit = SubmitField('Login')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(min=8, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('Email', validators=[DataRequired(), Length(min=8, max=64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=128)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[            
        ('user', 'user'),
        ('guest', 'guest'),      
    ], validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')
        
        
class AccessForm(FlaskForm):
    # This will create checkboxes for all permissions dynamically
    permissions = SelectMultipleField(
        'Permissions',
        coerce=int,  # We use `int` because the permission ID is an integer
        option_widget=widgets.CheckboxInput(),  # Use checkboxes
        widget=widgets.ListWidget(prefix_label=False),  # Arrange them in a list
        # validators=[DataRequired()]  # Ensure the form gets at least one permission selected
    )

    def __init__(self, *args, **kwargs):
        super(AccessForm, self).__init__(*args, **kwargs)
        # Dynamically fetch permissions from the database
        self.permissions.choices = [(perm.id, perm.name) for perm in Permission.query.all()]

class UserApprovalForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    approved = BooleanField('Approved', default=None)
    approve = SubmitField('Approve') 
    reject = SubmitField('Reject')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id.choices = [(user.id, user.name) for user in User.query.filter_by(approved=None).all()]

class UserPermissionForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    permission_id = SelectMultipleField('Permissions', coerce=int, option_widget=widgets.CheckboxInput(), widget=widgets.ListWidget(prefix_label=False))
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id.choices = [(user.id, user.name) for user in User.query.all()]
        self.permission_id.choices = [(perm.id, perm.name) for perm in Permission.query.all()]
        
class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(min=8, max=64)])
    submit = SubmitField('Submit')
    
class ResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(min=8, max=64)])
    otp = PasswordField('OTP', validators=[DataRequired(), Length(min=6, max=6)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=128)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Submit')