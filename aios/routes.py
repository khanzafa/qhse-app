# aios/routes.py
from flask import Blueprint, render_template, flash, redirect, request, url_for, Response, stream_with_context, abort, jsonify
from flask_login import current_user, login_user, logout_user, login_required

aios = Blueprint('aios', __name__)

@aios.route('/aios')
@login_required
def index():
    return render_template('aios/base.html')