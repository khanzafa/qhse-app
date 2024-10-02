from collections import Counter
from datetime import datetime, timedelta
import random
from flask import Blueprint, Response, abort, render_template, redirect, request, url_for, flash, session, jsonify
from flask_login import login_required
from app.models import CCTV, CCTVLocation, DetectedObject, Detector, DetectorType, Weight
from app import db
import logging
from utils.auth import get_allowed_permission_ids
from sqlalchemy.orm import joinedload

logging.basicConfig(level=logging.DEBUG)

report_bp = Blueprint('report', __name__, url_prefix='/report')

# REPORT
# @report_bp.route("/dashboard")
# @login_required
# def dashboard():
#     session_permission = session.get('permission_id')

#     num_cctv = CCTV.query.filter_by(permission_id=session_permission).count()
#     num_detectors = Detector.query.filter_by(permission_id=session_permission).count()

#     current_date = datetime.utcnow()
#     seven_days_ago = current_date - timedelta(days=7)

#     daily_counts = (
#         db.session.query(
#             db.func.DATE(DetectedObject.timestamp).label('detection_date'),
#             db.func.count(DetectedObject.id).label('count')
#         )
#         .filter(
#             DetectedObject.permission_id == session_permission,
#             DetectedObject.timestamp >= seven_days_ago
#         )
#         .group_by(db.func.DATE(DetectedObject.timestamp))
#         .order_by(db.func.DATE(DetectedObject.timestamp))
#         .all()
#     )

#     daily_counts_dict = {row.detection_date: row.count for row in daily_counts}
#     daily_detected_object_counts = [daily_counts_dict.get((current_date - timedelta(days=i)).date(), 0) for i in range(7)]

#     last_7_days = [(current_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

#     results = (
#         db.session.query(
#             CCTV.cctv_location,
#             db.func.count(DetectedObject.id).label('count')
#         )
#         .join(Detector, DetectedObject.detector_id == Detector.id)
#         .join(CCTV, Detector.cctv_id == CCTV.id)
#         .filter(
#             DetectedObject.permission_id == session_permission,
#             DetectedObject.timestamp >= seven_days_ago
#         )
#         .group_by(CCTV.cctv_location)
#         .all()
#     )

    
#     detected_objects_by_location = {location: count for location, count in results}
#     locations, counts = zip(*detected_objects_by_location.items()) if detected_objects_by_location else ([], [])

#     results_object_types = (
#     db.session.query(
#         DetectedObject.name,
#         db.func.count(DetectedObject.id).label('count')
#     )
#     .filter(DetectedObject.permission_id == session_permission)
#     .group_by(DetectedObject.name)
#     .order_by(db.func.count(DetectedObject.id).desc())
#     .limit(10)  # Limit to top 10 detected object types
#     .all()
#     )

#     detected_objects_types = {name: count for name, count in results_object_types}
#     object_types, object_counts = zip(*detected_objects_types.items()) if detected_objects_types else ([], [])

#     return render_template(
#         'dashboard.html',
#         num_cctv=num_cctv,
#         detected_objects_by_location=detected_objects_by_location,
#         num_detectors=num_detectors,
#         last_7_days=last_7_days,
#         session_permission=session_permission,
#         num_all_detection=DetectedObject.query.filter_by(permission_id=session_permission).count(),
#         count_of_detected_object=DetectedObject.query.filter(
#             DetectedObject.permission_id == session_permission,
#             DetectedObject.name.isnot(None)
#         ).count(),
#         daily_detected_object_counts=daily_detected_object_counts,
#         locations=locations,
#         counts=counts,
#         object_types=object_types,
#         object_counts=object_counts
#     )

@report_bp.route("/dashboard")
@login_required
def dashboard():
    detected_objects = DetectedObject.query \
                            .join(Detector, DetectedObject.detector_id == Detector.id) \
                            .join(CCTV, Detector.cctv_id == CCTV.id) \
                            .join(DetectorType, Detector.detector_type_id == DetectorType.id) \
                            .join(CCTVLocation, CCTV.cctv_location_id == CCTVLocation.id) \
                            .join(Weight, Detector.weight_id == Weight.id) \
                            .filter(DetectedObject.permission_id == session.get('permission_id')) \
                            .order_by(DetectedObject.timestamp.desc()) \
                            .all()
    
    cctv_locations = CCTVLocation.query.all()
    
    # Data struktur untuk pie chart berdasarkan tipe CCTV
    detected_objects_by_cctv_type = {}    
    for location in cctv_locations:
        types_counter = Counter([detected_object.detector.cctv.type for detected_object in detected_objects if detected_object.detector.cctv.cctv_location_id == location.id])
        detected_objects_by_cctv_type[location.name] = types_counter
    
    for location, types_counter in detected_objects_by_cctv_type.items():
        sorted_types_counter = dict(sorted(types_counter.items(), key=lambda item: item[1], reverse=True))
        top_3_types = dict(list(sorted_types_counter.items())[:3])
        other_types = dict(list(sorted_types_counter.items())[3:])
        detected_objects_by_cctv_type[location] = top_3_types
        detected_objects_by_cctv_type[location]['Other'] = sum(other_types.values())

    # Data struktur untuk bar chart berdasarkan hari dalam 7 hari terakhir
    daily_counts = Counter([detected_object.timestamp.date() for detected_object in detected_objects])
    last_7_days = [(max(daily_counts) - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    daily_detected_object_counts = [daily_counts.get(datetime.strptime(day, '%Y-%m-%d').date(), 0) for day in last_7_days]
    
    # Data Struktur untuk scatter plot berdasarkan lokasi CCTV
    detected_objects_by_location = Counter([detected_object.detector.cctv.cctv_location_id for detected_object in detected_objects])
    scatter_data = []
    for location in cctv_locations:
        location_id = location.id
        count = detected_objects_by_location.get(location_id, 0)  # Jumlah detected objects
        scatter_data.append({
            'name': location.name,  # Nama lokasi
            'x': random.uniform(0, 100),  # Koordinat x
            'y': random.uniform(0, 100),  # Koordinat y
            'count': count  # Jumlah objek yang terdeteksi
        })

    # Jumlah data
    cctv_count = CCTV.query.count()
    weight_count = Weight.query.count()
    detector_count = Detector.query.count()
    detected_object_count = DetectedObject.query.count()

    return render_template('new_dashboard.html', 
                           detected_objects_by_cctv_type=detected_objects_by_cctv_type, 
                            last_7_days=last_7_days,
                            daily_detected_object_counts=daily_detected_object_counts,   
                            scatter_data=scatter_data,    
                            cctv_count=cctv_count,
                            weight_count=weight_count,
                            detector_count=detector_count,
                            detected_object_count=detected_object_count,                       
                            cctv_locations=cctv_locations)

@report_bp.route('/detected-object', methods=['GET'])
@login_required
def detected_object():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Jumlah objek per halaman
    search_query = request.args.get('search_query')

    if search_query:
        detected_objects = DetectedObject.query.join(Detector).join(CCTV).join(CCTVLocation) \
            .filter(db.or_(DetectedObject.name.like(f'%{search_query}%'), CCTVLocation.name.like(f'%{search_query}%'), CCTV.type.like(f'%{search_query}%',)), DetectedObject.permission_id == session.get('permission_id')) \
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