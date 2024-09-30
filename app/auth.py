from datetime import datetime, timedelta
from functools import wraps
import os
import random
from flask import Blueprint, render_template, flash, redirect, session, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
import pytz
from app import db
from app.models import User, Guest
from app.forms import ForgotPasswordForm, LoginForm, RegistrationForm, OTPForm, ResetPasswordForm
from flask_mail import Message
from colorama import Fore, Back, Style

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.menu'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            # if user.password_hash != form.password.data:
            flash('Invalid email or password')
            return redirect(url_for('auth.login'))
            
        if not user.approved:
            print('Not Approved')
            flash('Your account is not approved. Please contact the administrator.')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        if user.is_admin():
            return redirect(url_for('admin.menu'))    
        return redirect(url_for('main.index'))        
    return render_template('login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('role', None)
    return redirect(url_for('auth.login'))


def otp_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        otp_expiry = session.get('otp_expiry')
        if not otp_expiry or datetime.now(pytz.utc) > otp_expiry:
            return redirect(url_for('auth.guidebot_login'))
        return func(*args, **kwargs)
    return wrapper

@auth.route("/guidebot_login", methods=['GET', 'POST'])
def guidebot_login():
    # if current_user.is_authenticated:
    #     print("User authenticated")
    #     return redirect(url_for('guide_bot.chat'))
    
    form = OTPForm()
    if form.validate_on_submit():
        email = form.email.data
        password_or_otp = form.otp.data  # OTP is used as a password in the form
        
        action = request.form.get('action')

        # Determine which action to take based on the form button pressed
        if action == 'login':
            # Handle login action
            # Check if the user exists in the database
            if 'otp' not in session or session.get('otp_email') != email:
                flash('Invalid OTP or email.', 'danger')
                return redirect(url_for('auth.guidebot_login'))

            if session.get('otp') != password_or_otp:
                flash('Invalid OTP. Please try again.', 'danger')
                return redirect(url_for('auth.guidebot_login'))
            
            print("date time now:", datetime.now(pytz.utc))
            print('otp expiry', session.get('otp_expiry'))
            
            # Get the current time in UTC
            if datetime.now(pytz.utc) > session.get('otp_expiry'):
                flash('OTP expired. Please request a new one.', 'danger')
                return redirect(url_for('auth.guidebot_login'))
            
            print(Fore.BLUE)
            print(f"Session OTP Email: {session.get('otp_email')}")
            print(f"Session OTP: {session.get('otp')}")
            print(f"Session OTP Expiry: {session.get('otp_expiry')}")
            print(Style.RESET_ALL)

            print("LOGIN")
            # Redirect to the chat page after successful login
            return redirect(url_for('aios.index'))
        
        elif action == 'request_otp':
            # Handle OTP request action
            if not email:
                flash('Email is required to request an OTP.', 'danger')
                return redirect(url_for('auth.guidebot_login'))

            # Generate OTP and set expiry time
            otp = generate_otp()
            expiry_time = datetime.now() + timedelta(minutes=OTP_EXPIRY_TIME)

            # Store OTP and expiry time in session
            session['otp'] = otp
            session['otp_expiry'] = expiry_time
            session['otp_email'] = email
            print(Fore.BLUE)
            print(f"Generated OTP: {otp}, Expiry: {expiry_time}")
            print(f"Session OTP Email: {session.get('otp_email')}")
            print(f"Session OTP: {session.get('otp')}")
            print(f"Session OTP Expiry: {session.get('otp_expiry')}")
            print(Style.RESET_ALL)

            # Send OTP via email
            from app import mail
            msg = Message(subject='Your OTP for Guidebot Login', sender=os.getenv('MAIL_USERNAME'), recipients=[email])
            msg.body = f"Your OTP is {otp}. It will expire in {OTP_EXPIRY_TIME} minutes."

            try:
                mail.send(msg)
                flash('An OTP has been sent to your email. Please check your inbox.', 'info')
            except Exception as e:
                print(f"Error sending email: {e}")
                flash('Failed to send OTP to email. Please try again later.', 'danger')
            print("REQ OTP")
            return redirect(url_for('auth.guidebot_login'))
        
    return render_template('guide_bot/guidebot_login.html', form=form)

def generate_otp():
    return str(random.randint(100000, 999999))  # 6-digit OTP

OTP_EXPIRY_TIME = 3  # minutes

@auth.route("/guidebot_logout", methods=['GET', 'POST'])
def guidebot_logout():
    # Clear OTP data from session after successful login
    session.pop('otp', None)
    session.pop('otp_expiry', None)
    session.pop('otp_email', None)
    return redirect(url_for('auth.guidebot_login'))
    
@auth.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        # user = User.query.filter_by(email=form.email.data).first()
        session['otp_email'] = form.email.data
        if form.email.data:
            send_password_reset_email()
        else:
            flash('Email not found. Please register first.', 'danger')
        return redirect(url_for('auth.reset_password'))
    return render_template('forgot_password.html', form=form)

def send_password_reset_email():
    otp = generate_otp()
    expiry_time = datetime.now() + timedelta(minutes=OTP_EXPIRY_TIME)
    
    # Store OTP and expiry time in session
    session['otp'] = otp
    session['otp_expiry'] = expiry_time
    
    # Send OTP via email
    from app import mail
    msg = Message(subject='Your OTP for Forgot Password', sender=os.getenv('MAIL_USERNAME'), recipients=[session.get('otp_email')])
    msg.body = f"Your OTP is {otp}. It will expire in {OTP_EXPIRY_TIME} minutes."

    try:
        mail.send(msg)
        flash('An OTP has been sent to your email. Please check your inbox.', 'info')
    except Exception as e:
        print(f"Error sending email: {e}")
        flash('Failed to send OTP to email. Please try again later.', 'danger')
    print("REQ OTP")
    
    
@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        if form.otp.data == session.get('otp'):
            if form.password.data == form.password2.data:
                user = User.query.filter_by(email=session.get('otp_email')).first()
                if user:
                    user.set_password(form.password.data)
                    # user.password_hash = form.password.data
                    db.session.commit()
                    flash('Password reset successful. You can now login.', 'success')
                    return redirect(url_for('auth.login'))
                else:
                    flash('User not found. Please register first.', 'danger')
            else:
                flash('Passwords do not match. Please try again.', 'danger')
        else:   
            flash('Invalid OTP. Please try again.', 'danger')
    return render_template('reset_password.html', form=form)