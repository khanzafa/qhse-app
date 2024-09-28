from app.routes.cctv import cctv_bp
from app.routes.contact import contact_bp
from app.routes.detector import detector_bp
from app.routes.document import document_bp
from app.routes.message import message_bp
from app.routes.notification import notification_bp
from app.routes.report import report_bp
from app.routes.weight import weight_bp
from app.routes.admin import admin_bp

app_routes = [
    cctv_bp,
    contact_bp,
    detector_bp,
    document_bp,
    message_bp,
    notification_bp,
    report_bp,
    weight_bp,
    admin_bp,

]



import base64
import io
import os
import re
import cv2
import pandas as pd

# import plotly.graph_objects as go
# import plotly.io as pio
import requests
from datetime import datetime, timedelta
from collections import Counter
from flask import (
    Blueprint,
    render_template,
    flash,
    redirect,
    request,
    send_from_directory,
    session,
    url_for,
    Response,
    stream_with_context,
    abort,
    jsonify,
)
from app.extensions import db
from app.models import (
    CCTV,
    Contact,
    DetectedObject,
    Detector,
    DetectorType,
    MessageTemplate,
    NotificationRule,
    Permission,
    User,
    UserPermission,
    Weight,
    suMenu,
)
from app.forms import (
    AccessForm,
    AddCCTVForm,
    EditCCTVForm,
    MessageTemplateForm,
    ModelForm,
    NotificationRuleForm,
    SelectCCTVForm,
    ContactForm,
    DetectorForm,
    LoginForm,
    RegistrationForm,
)
# from app import gesture_detector, ppe_detector, unfocused_detector
from flask_login import current_user, login_user, logout_user, login_required
import logging

from utils.auth import get_allowed_permission_ids

main = Blueprint("main", __name__)
# current_user = {'name': 'John'}
GRAPHICS_DIR = "app/static/graphics"

@main.route("/", methods=["GET"])
@login_required
def index():    
    # Get the permission IDs for the current user
    allowed_permission_ids = get_allowed_permission_ids()    
    
    # Query the suMenu model for menus associated with those permission IDs
    menus = suMenu.query.filter(suMenu.permission_id.in_(allowed_permission_ids)).all()
    
    # Render the index template and pass the menu data
    return render_template("index.html", menus=menus)


@main.route('/report/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    session_permission = session.get('permission_id')

    num_cctv = CCTV.query.filter_by(permission_id=session_permission).count()
    num_detectors = Detector.query.filter_by(permission_id=session_permission).count()

    current_date = datetime.utcnow()
    seven_days_ago = current_date - timedelta(days=7)

    daily_counts = (
        db.session.query(
            db.func.DATE(DetectedObject.timestamp).label('detection_date'),
            db.func.count(DetectedObject.id).label('count')
        )
        .filter(
            DetectedObject.permission_id == session_permission,
            DetectedObject.timestamp >= seven_days_ago
        )
        .group_by(db.func.DATE(DetectedObject.timestamp))
        .order_by(db.func.DATE(DetectedObject.timestamp))
        .all()
    )

    daily_counts_dict = {row.detection_date: row.count for row in daily_counts}
    daily_detected_object_counts = [daily_counts_dict.get((current_date - timedelta(days=i)).date(), 0) for i in range(7)]

    last_7_days = [(current_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    results = (
        db.session.query(
            CCTV.location,
            db.func.count(DetectedObject.id).label('count')
        )
        .join(Detector, DetectedObject.detector_id == Detector.id)
        .join(CCTV, Detector.cctv_id == CCTV.id)
        .filter(
            DetectedObject.permission_id == session_permission,
            DetectedObject.timestamp >= seven_days_ago
        )
        .group_by(CCTV.location)
        .all()
    )

    
    detected_objects_by_location = {location: count for location, count in results}
    locations, counts = zip(*detected_objects_by_location.items()) if detected_objects_by_location else ([], [])

    results_object_types = (
    db.session.query(
        DetectedObject.name,
        db.func.count(DetectedObject.id).label('count')
    )
    .filter(DetectedObject.permission_id == session_permission)
    .group_by(DetectedObject.name)
    .order_by(db.func.count(DetectedObject.id).desc())
    .limit(10)  # Limit to top 10 detected object types
    .all()
    )

    detected_objects_types = {name: count for name, count in results_object_types}
    object_types, object_counts = zip(*detected_objects_types.items()) if detected_objects_types else ([], [])

    return render_template(
        'dashboard.html',
        num_cctv=num_cctv,
        detected_objects_by_location=detected_objects_by_location,
        num_detectors=num_detectors,
        last_7_days=last_7_days,
        session_permission=session_permission,
        num_all_detection=DetectedObject.query.filter_by(permission_id=session_permission).count(),
        count_of_detected_object=DetectedObject.query.filter(
            DetectedObject.permission_id == session_permission,
            DetectedObject.name.isnot(None)
        ).count(),
        daily_detected_object_counts=daily_detected_object_counts,
        locations=locations,
        counts=counts,
        object_types=object_types,
        object_counts=object_counts
    )






@main.route('/set_session', methods=['POST'])
def set_session():
    permission_id = request.form.get('id')    
    if permission_id:
        permission = Permission.query.get(permission_id)
        session['permission_name'] = permission.name
        session['permission_id'] = permission_id
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'No ID provided'}), 400

@main.app_context_processor
def inject_session_permission():
    return dict(session_permission=session.get('permission_id', ''), permission_name=session.get('permission_name', ''))