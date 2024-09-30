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

    num_cctv = CCTV.query.count()
    num_detectors = Detector.query.count()

    # Deklarasi filter untuk permission_id 1 dan 2
    filter_permission_1 = [DetectedObject.permission_id == 1]
    filter_permission_2 = [DetectedObject.permission_id == 2]

    # Gunakan session_permission untuk menentukan filter mana yang dipakai
    if session_permission == 1:
        detection_filters = filter_permission_1
    elif session_permission == 2:
        detection_filters = filter_permission_2
    else:
        detection_filters = []  # Jika tidak ada permission yang sesuai

    # Menghitung jumlah deteksi berdasarkan jenis objek
    detection_counts = {
        "no_helmet": DetectedObject.query.filter(DetectedObject.name == "no-helmet", *detection_filters).count(),
        "no_vest": DetectedObject.query.filter(DetectedObject.name == "no-vest", *detection_filters).count(),
        "drowsy": DetectedObject.query.filter(DetectedObject.name == "drowsy", *detection_filters).count(),
        "phone": DetectedObject.query.filter(DetectedObject.name == "phone", *detection_filters).count(),
        "no_seatbelt": DetectedObject.query.filter(DetectedObject.name == "no-seatbelt", *detection_filters).count(),
        "danger": DetectedObject.query.filter(DetectedObject.name == "cross-hand", *detection_filters).count(),
        "fire": DetectedObject.query.filter(DetectedObject.name == "fire", *detection_filters).count(),
        "smoke": DetectedObject.query.filter(DetectedObject.name == "smoke", *detection_filters).count(),
        "sleep": DetectedObject.query.filter(DetectedObject.name == "sleep", *detection_filters).count()
    }

    num_no_ppe_detected = detection_counts["no_helmet"] + detection_counts["no_vest"]
    num_reckless_driver_detected = detection_counts["drowsy"] + detection_counts["phone"] + detection_counts["no_seatbelt"]

    results = db.session.query(DetectedObject, CCTV).select_from(DetectedObject) \
        .join(Detector).join(CCTV) \
        .filter(*detection_filters).all()

    cameras = {camera.id: camera.location for obj, camera in results}
    cameras = {'all': "All Cameras", **cameras}

    selected_camera_ppe = request.form.get('camera', 'all')
    selected_camera_driver = request.form.get('camera', 'all')
    selected_camera_danger = request.form.get('camera', 'all')
    selected_camera_paier = request.form.get('camera', 'all')

    def filter_by_camera(camera_id, object_name):
        query = db.session.query(DetectedObject).filter(DetectedObject.name == object_name, *detection_filters)
        if camera_id != 'all':
            query = query.join(Detector).join(CCTV).filter(CCTV.id == camera_id)
        return query.count()

    total_no_helmet_all = filter_by_camera(selected_camera_ppe, 'no-helmet')
    total_no_vest_all = filter_by_camera(selected_camera_ppe, 'no-vest')
    total_drowsy_all = filter_by_camera(selected_camera_driver, 'drowsy')
    total_no_seatbelt_all = filter_by_camera(selected_camera_driver, 'no-seatbelt')
    total_phone_all = filter_by_camera(selected_camera_driver, 'phone')
    total_reckless_all = total_drowsy_all + total_no_seatbelt_all + total_phone_all
    total_gesture_help_all = filter_by_camera(selected_camera_danger, 'cross-hand')
    total_fire_help_all = filter_by_camera(selected_camera_paier, 'fire')
    total_smoke_help_all = filter_by_camera(selected_camera_paier, 'smoke')
    total_sleep_help_all = filter_by_camera(selected_camera_paier, 'sleep')

    latest_entry = DetectedObject.query.filter(*detection_filters).order_by(DetectedObject.timestamp.desc()).first()
    latest_date = latest_entry.timestamp if latest_entry else datetime.utcnow()
    earliest_date = latest_date - timedelta(days=7)

    today = datetime.today()
    last_7_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    def fetch_daily_counts(object_name, camera_id):
        counts = []
        for i in range(7):
            query = db.session.query(DetectedObject).filter(
                DetectedObject.name == object_name,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i)),
                *detection_filters
            )
            if camera_id != 'all':
                query = query.join(Detector).join(CCTV).filter(CCTV.id == camera_id)
            counts.append(query.count())
        return counts

    num_no_vest_detected_per_day = fetch_daily_counts('no-vest', selected_camera_ppe)
    num_no_helmet_detected_per_day = fetch_daily_counts('no-helmet', selected_camera_ppe)
    
    num_drowsy_detected_per_day = fetch_daily_counts('drowsy', selected_camera_driver)
    num_phone_detected_per_day = fetch_daily_counts('phone', selected_camera_driver)
    num_no_seatbelt_detected_per_day = fetch_daily_counts('no-seatbelt', selected_camera_driver)

    num_danger_gesture_detected_per_day = fetch_daily_counts('cross-hand', selected_camera_danger)
    
    num_fire_detected_per_day = fetch_daily_counts('fire', selected_camera_paier)
    num_smoke_detected_per_day = fetch_daily_counts('smoke', selected_camera_paier)
    num_sleep_detected_per_day = fetch_daily_counts('sleep', selected_camera_paier)
    return render_template(
        'dashboard.html',
        num_cctv=num_cctv,
        num_detectors=num_detectors,
        num_no_helmet_detected=detection_counts["no_helmet"],
        num_no_vest_detected=detection_counts["no_vest"],
        num_fire_detected=detection_counts["fire"],
        num_smoke_detected=detection_counts["smoke"],
        num_sleep_detected=detection_counts["sleep"],
        num_no_ppe_detected=num_no_ppe_detected,
        num_reckless_driver_detected=num_reckless_driver_detected,
        num_danger_detected=detection_counts["danger"],
        cameras=cameras,
        last_7_days=last_7_days,
        num_no_vest_detected_per_day=num_no_vest_detected_per_day,
        num_no_helmet_detected_per_day=num_no_helmet_detected_per_day,
        num_drowsy_detected_per_day=num_drowsy_detected_per_day,
        num_phone_detected_per_day=num_phone_detected_per_day,
        num_no_seatbelt_detected_per_day=num_no_seatbelt_detected_per_day,
        num_danger_gesture_detected_per_day=num_danger_gesture_detected_per_day,
        num_fire_detected_per_day=num_fire_detected_per_day,
        num_smoke_detected_per_day=num_smoke_detected_per_day,
        num_sleep_detected_per_day=num_sleep_detected_per_day,
        session_permission=session_permission
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