from collections import Counter
from datetime import timedelta
from flask import Blueprint, Response, abort, render_template, redirect, request, url_for, flash, session, jsonify
from flask_login import login_required
from app.models import *
from app import db
from app.forms import *
import logging
from utils.auth import get_allowed_permission_ids
from sqlalchemy.orm import joinedload

logging.basicConfig(level=logging.DEBUG)

report_bp = Blueprint('report', __name__, url_prefix='/report')

# REPORT
@report_bp.route("/dashboard")
@login_required
def dashboard():
    session_permission = session.get('permission_id')

    # Agregasi data terkait jumlah CCTV, detektor, dan PPE
    num_cctv = CCTV.query.filter(CCTV.permission_id == session.get('permission_id')).count()
    num_detectors = Detector.query.filter(Detector.permission_id == session.get('permission_id')).count()

    num_no_helmet = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "no-helmet").count()
    num_no_vest = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "no-vest").count()
    num_no_ppe = num_no_helmet + num_no_vest
    num_drowsy = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "drowsy").count()
    num_phone = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "phone").count()
    num_no_seatbelt = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "no-seatbelt").count()
    num_reckless = num_drowsy + num_phone + num_no_seatbelt
    num_danger = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "cross-hand").count()
    
    # Ambil semua kamera
    results = db.session.query(DetectedObject, CCTV).select_from(DetectedObject) \
        .join(Detector) \
        .join(CCTV) \
        .all()

    # Buat dictionary kamera
    cameras = {camera.id: camera.location for obj, camera in results}
    cameras = {'all': f"All Cameras", **cameras}

    # Dapatkan kamera yang dipilih dari form atau set 'all' sebagai default
    selected_camera_ppe = request.form.get('camera', 'all')
    selected_camera_driver = request.form.get('camera', 'all')
    selected_camera_danger = request.form.get('camera', 'all')
    
    
    # Filter data berdasarkan kamera yang dipilih
    if selected_camera_ppe == 'all':
        # Mengambil semua data untuk semua kamera
        total_no_helmet_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'no-helmet').count()
        total_no_vest_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'no-vest').count()
    else:
        # Mengambil data berdasarkan kamera yang dipilih
        data = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'),CCTV.id == selected_camera_ppe).all()

        total_no_helmet_all = sum(1 for obj in data if obj.name == 'no-helmet')
        total_no_vest_all = sum(1 for obj in data if obj.name == 'no-vest')
            
    
    # Filter data berdasarkan kamera yang dipilih
    if selected_camera_driver == 'all':
        # Mengambil semua data untuk semua kamera
        total_drowsy_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'drowsy').count()
        total_no_seatbelt_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'no-seatbelt').count()
        total_phone_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'phone').count()
        total_reckless_all = total_drowsy_all + total_no_seatbelt_all + total_phone_all
    else:
        # Mengambil data berdasarkan kamera yang dipilih
        data = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_driver).all()

        total_drowsy_all = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_driver, DetectedObject.name == 'drowsy').count()
        total_no_seatbelt_all = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_driver, DetectedObject.name == 'no-seatbelt').count()
        total_phone_all = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_driver, DetectedObject.name == 'phone').count()
        total_reckless_all = total_drowsy_all + total_no_seatbelt_all + total_phone_all
            
            
    # Filter data berdasarkan kamera yang dipilih
    if selected_camera_danger == 'all':
        # Mengambil semua data untuk semua kamera
        total_gesture_help_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'cross-hand').count()
    else:
        # Mengambil data berdasarkan kamera yang dipilih
        data = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_danger).all()
        total_gesture_help_all = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_danger, DetectedObject.name == 'cross-hand').count()

    # Ambil tanggal terbaru dan terawal dari data
    latest_entry = DetectedObject.query.order_by(DetectedObject.timestamp.desc()).first()
    if latest_entry:
        latest_date = latest_entry.timestamp
    else:
        latest_date = datetime.utcnow()

    earliest_date = latest_date - timedelta(days=7)

        # Example data for PPE detection per day
    today = datetime.today()
    last_7_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    
    # Buat array untuk data harian
    num_no_vest_per_day = []
    num_no_helmet_per_day = []
    num_drowsy_per_day = []
    num_phone_per_day = []
    num_no_seatbelt_per_day = []
    num_danger_per_day = []


    # Fetch daily counts for no-vest and no-helmet
    if selected_camera_ppe == 'all':
        num_no_vest_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-vest',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

        num_no_helmet_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-helmet',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
    else:
        num_no_vest_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-vest',
                CCTV.id == selected_camera_ppe,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

        num_no_helmet_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-helmet',
                CCTV.id == selected_camera_ppe,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]


    # Fetch daily counts for driver
    if selected_camera_driver == 'all':
        num_drowsy_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'drowsy',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

        num_phone_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'phone',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
        
        num_no_seatbelt_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-seatbelt',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
                
    else:
        num_drowsy_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'drowsy',
                CCTV.id == selected_camera_driver,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

        num_phone_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'phone',
                CCTV.id == selected_camera_driver,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
        
        num_no_seatbelt_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-seatbelt',
                CCTV.id == selected_camera_driver,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

    # Fetch daily counts for danger
    if selected_camera_driver == 'all':
        num_danger_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'cross-hand',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
    else:
        num_danger_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'cross-hand',
                CCTV.id == selected_camera_danger,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

    # Hitung total harian untuk menampilkan di template
    total_no_vest = sum(num_no_vest_per_day) or 0
    total_no_helmet = sum(num_no_helmet_per_day) or 0
    total_no_ppe = sum(num_no_helmet_per_day + num_no_vest_per_day)
    total_drowsy = sum(num_drowsy_per_day) or 0
    total_phone = sum(num_phone_per_day) or 0
    total_no_seatbelt = sum(num_no_seatbelt_per_day) or 0
    total_reckless_driver = sum(num_drowsy_per_day + num_phone_per_day + num_no_seatbelt_per_day) or 0
    total_danger = sum(num_danger_per_day) or 0


    # Render data ke template dashboard
    return render_template(
        'dashboard.html',
        cameras=cameras,
        selected_camera_ppe=selected_camera_ppe,
        selected_camera_driver=selected_camera_driver,
        selected_camera_danger=selected_camera_danger,
        num_cctv=num_cctv,
        num_detectors=num_detectors,
        num_no_ppe=num_no_ppe,
        num_no_helmet=total_no_helmet_all,
        num_no_vest=num_no_vest,
        num_drowsy=total_drowsy_all,
        num_no_seatbelt=total_no_seatbelt_all,
        num_phone=total_phone_all,
        num_reckless=num_reckless,
        num_danger=num_danger,
        last_7_days=last_7_days,
        num_no_vest_per_day=num_no_vest_per_day,
        num_no_helmet_per_day=num_no_helmet_per_day,
        num_drowsy_per_day=num_drowsy_per_day,
        num_phone_per_day=num_phone_per_day,
        num_no_seatbelt_per_day=num_no_seatbelt_per_day,
        num_danger_per_day=num_danger_per_day,
    )

@report_bp.route('/detected-object', methods=['GET'])
@login_required
def detected_object():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Jumlah objek per halaman
    search_query = request.args.get('search_query')

    if search_query:
        detected_objects = DetectedObject.query.join(Detector).join(CCTV) \
            .filter(DetectedObject.name.like(f'%{search_query}%'), DetectedObject.permission_id == session.get('permission_id')) \
            .order_by(DetectedObject.timestamp.desc()) \
            .paginate(page=page, per_page=per_page)
    else:
        detected_objects = DetectedObject.query.join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id')) \
            .order_by(DetectedObject.timestamp.desc()) \
            .paginate(page=page, per_page=per_page)

    return render_template('detected_object.html', detected_objects=detected_objects, search_query=search_query)

@report_bp.route('/detected-object/view-object/<int:object_id>', methods=['GET'])
@login_required
def view_object(object_id):
    detected_object = DetectedObject.query.get_or_404(object_id)    
    return render_template('view_object.html', detected_object=detected_object)   