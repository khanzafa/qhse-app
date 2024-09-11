# aios/routes.py
from flask import Blueprint, render_template, flash, redirect, request, session, url_for, Response, stream_with_context, abort, jsonify
from flask_login import current_user, login_user, logout_user, login_required

from app.auth import otp_required

aios = Blueprint('aios', __name__)

@aios.route('/aios')
@login_required
def index():
    # Clear OTP data from session after successful login
    session.pop('otp', None)
    session.pop('otp_expiry', None)
    session.pop('otp_email', None)
    return render_template('aios/base.html')