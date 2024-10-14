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
#     detected_objects = DetectedObject.query \
#                             .join(Detector, DetectedObject.detector_id == Detector.id) \
#                             .join(CCTV, Detector.cctv_id == CCTV.id) \
#                             .join(DetectorType, Detector.detector_type_id == DetectorType.id) \
#                             .join(CCTVLocation, CCTV.cctv_location_id == CCTVLocation.id) \
#                             .join(Weight, Detector.weight_id == Weight.id) \
#                             .filter(DetectedObject.permission_id == session.get('permission_id')) \
#                             .order_by(DetectedObject.timestamp.desc()) \
#                             .all()
    
#     cctv_locations = CCTVLocation.query.all()
    
#     # Data struktur untuk pie chart berdasarkan tipe CCTV
#     # Ambil semua CCTV berdasarkan lokasi
#     cctv_by_location = {location.id: CCTV.query.filter_by(cctv_location_id=location.id).all() for location in cctv_locations}

#     # Data struktur untuk pie chart berdasarkan tipe CCTV dan jumlah objek yang terdeteksi per tipe
#     detected_objects_by_cctv_type = {}

#     for location in cctv_locations:
#         # Hitung jumlah objek yang terdeteksi per tipe CCTV di lokasi tersebut
#         types_counter = Counter()
        
#         # Looping untuk setiap CCTV di lokasi
#         for cctv in cctv_by_location[location.id]:
#             # Hitung jumlah objek yang terdeteksi untuk setiap tipe CCTV
#             detected_object_count = DetectedObject.query \
#                 .join(Detector, DetectedObject.detector_id == Detector.id) \
#                 .filter(Detector.cctv_id == cctv.id) \
#                 .count()
            
#             # Tambahkan hasil ke counter
#             types_counter[cctv.type] += detected_object_count
        
#         detected_objects_by_cctv_type[location.name] = types_counter
        
#     print(detected_objects_by_cctv_type)
#     for location, types_counter in detected_objects_by_cctv_type.items():
#         sorted_types_counter = dict(sorted(types_counter.items(), key=lambda item: item[1], reverse=True))
#         top_3_types = dict(list(sorted_types_counter.items())[:3])
#         other_types = dict(list(sorted_types_counter.items())[3:])
#         detected_objects_by_cctv_type[location] = top_3_types
#         detected_objects_by_cctv_type[location]['Other'] = sum(other_types.values())

#     # Data struktur untuk bar chart berdasarkan hari dalam 7 hari terakhir
#     # After defining daily_counts
#     daily_counts = Counter([detected_object.timestamp.date() for detected_object in detected_objects])


#     # Check if daily_counts is empty
#     if daily_counts:
#         # If not empty, proceed to get the last 7 days
#         last_day = max(daily_counts)
#         last_7_days = [(last_day - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
#     else:
#         # If empty, set last_7_days to an empty list or some default values
#         last_7_days = []

#     # Ensure daily_detected_object_counts has values for each day in last_7_days
#     daily_detected_object_counts = [daily_counts.get(datetime.strptime(day, '%Y-%m-%d').date(), 0) for day in last_7_days]

    
#     # Data Struktur untuk scatter plot berdasarkan lokasi CCTV
#     detected_objects_by_location = Counter([detected_object.detector.cctv.cctv_location_id for detected_object in detected_objects])
#     scatter_data = []
#     for location in cctv_locations:
#         location_id = location.id
#         count = detected_objects_by_location.get(location_id, 0)  # Jumlah detected objects
#         scatter_data.append({
#             'name': location.name,  # Nama lokasi
#             'x': random.uniform(0, 100),  # Koordinat x
#             'y': random.uniform(0, 100),  # Koordinat y
#             'count': count  # Jumlah objek yang terdeteksi
#         })

#     # Jumlah data
#     cctv_count = CCTV.query.count()
#     weight_count = Weight.query.count()
#     detector_count = Detector.query.count()
#     detected_object_count = DetectedObject.query.count()

#     return render_template('new_dashboard.html', 
#                            detected_objects_by_cctv_type=detected_objects_by_cctv_type, 
#                             last_7_days=last_7_days,
#                             daily_detected_object_counts=daily_detected_object_counts,   
#                             scatter_data=scatter_data,    
#                             cctv_count=cctv_count,
#                             weight_count=weight_count,
#                             detector_count=detector_count,
#                             detected_object_count=detected_object_count,                       
#                             cctv_locations=cctv_locations)


@report_bp.route("/dashboard")
@login_required
def dashboard():
    session_permission = session.get('permission_id')
    selected_location = request.args.get('location')
    cctv_locations = [loc.name for loc in db.session.query(CCTVLocation.name).distinct()]

    # Prepare the base query for DetectedObject
    detected_objects_query = (
        db.session.query(DetectedObject)
        .join(Detector, DetectedObject.detector_id == Detector.id)
        .join(CCTV, Detector.cctv_id == CCTV.id)
        .filter(DetectedObject.permission_id == session_permission)
    )
    
    if selected_location:
        detected_objects_query = detected_objects_query.filter(
            CCTV.cctv_location.has(name=selected_location)
        )

    # Execute the statistics queries
    all_cctv = db.session.query(CCTV).filter_by(permission_id=session_permission).count()
    all_detectors = db.session.query(Detector).filter_by(permission_id=session_permission).count()
    all_weight = db.session.query(Detector).filter(
        Detector.permission_id == session_permission,
        Detector.weight_id.isnot(None)
    ).count()
    all_detection = detected_objects_query.count()

    current_date = datetime.utcnow()
    seven_days_ago = current_date - timedelta(days=7)
    last_7_days = [(current_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    # Weekly detection counts
    weekly_counts = (
        detected_objects_query
        .filter(DetectedObject.timestamp >= seven_days_ago)
        .group_by(db.func.DATE(DetectedObject.timestamp))
        .order_by(db.func.DATE(DetectedObject.timestamp))
        .with_entities(db.func.DATE(DetectedObject.timestamp).label('detection_date'),
                       db.func.count(DetectedObject.id).label('count'))
        .all()
    )
    
    weekly_counts_dict = {row.detection_date: row.count for row in weekly_counts}
    weekly_detected_object_counts = [
        weekly_counts_dict.get((current_date - timedelta(days=i)).date(), 0) for i in range(7)
    ]

    # Weekly object types
    weekly_object_types_data = (
        detected_objects_query
        .filter(DetectedObject.timestamp >= seven_days_ago)
        .group_by(DetectedObject.name)
        .order_by(db.func.count(DetectedObject.id).desc())
        .limit(10)
        .with_entities(DetectedObject.name, db.func.count(DetectedObject.id).label('total_count'))
        .all()
    )
    
    weekly_object_types, weekly_object_counts = zip(*weekly_object_types_data) if weekly_object_types_data else ([], [])

    # Pie chart data (limit top 4 types and group others as 'Other')
    pie_chart_data = (
        detected_objects_query
        .group_by(CCTV.type)
        .with_entities(CCTV.type.label('type'), db.func.count(DetectedObject.id).label('count'))
        .order_by(db.func.count(DetectedObject.id).desc())
        .all()
    )

    pie_chart_types = [row.type for row in pie_chart_data]
    pie_chart_counts = [row.count for row in pie_chart_data]

    if len(pie_chart_types) > 4:
        other_count = sum(pie_chart_counts[4:])
        pie_chart_types = pie_chart_types[:4] + ['Other']
        pie_chart_counts = pie_chart_counts[:4] + [other_count]

    # 24-hour detections per hour
    start_time = current_date - timedelta(hours=24)
    hourly_counts = (
        detected_objects_query
        .filter(DetectedObject.timestamp >= start_time)
        .group_by(db.func.date_trunc('hour', DetectedObject.timestamp), CCTV.type)
        .with_entities(db.func.date_trunc('hour', DetectedObject.timestamp).label('detection_hour'),
                       CCTV.type.label('type'), db.func.count(DetectedObject.id).label('count'))
        .order_by(db.func.date_trunc('hour', DetectedObject.timestamp))
        .all()
    )

    hourly_counts_dict = {row.detection_hour: row.count for row in hourly_counts}
    last_24_hours_labels = [
        (current_date - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0) for i in range(24)
    ]
    hourly_detected_object_counts = [
        hourly_counts_dict.get(label, 0) for label in last_24_hours_labels
    ]

    # Daily object types for the last 24 hours
    daily_object_types_data = (
        detected_objects_query
        .filter(DetectedObject.timestamp >= start_time)
        .group_by(DetectedObject.name)
        .with_entities(DetectedObject.name, db.func.count(DetectedObject.id).label('total_count'))
        .order_by(db.func.count(DetectedObject.id).desc())
        .limit(10)
        .all()
    )

    daily_object_types, daily_object_counts = zip(*daily_object_types_data) if daily_object_types_data else ([], [])

    # Daily pie chart types
    daily_pie_chart_types = {}
    for row in hourly_counts:
        type_name = row.type
        count = row.count
        daily_pie_chart_types[type_name] = daily_pie_chart_types.get(type_name, 0) + count

    pie_chart_types_list = list(daily_pie_chart_types.keys())
    pie_chart_counts_list = list(daily_pie_chart_types.values())

    if len(pie_chart_types_list) > 4:
        other_count = sum(pie_chart_counts_list[4:])
        pie_chart_types_list = pie_chart_types_list[:4] + ['Other']
        pie_chart_counts_list = pie_chart_counts_list[:4] + [other_count]
    
    return render_template(
        'dashboard.html',
        all_cctv=all_cctv,
        all_weight=all_weight,
        all_detectors=all_detectors,
        all_detection=all_detection,
        last_7_days=last_7_days,
        session_permission=session_permission,
        weekly_detected_object_counts=weekly_detected_object_counts,
        weekly_object_types=weekly_object_types,
        weekly_object_counts=weekly_object_counts,
        daily_object_types=daily_object_types,
        daily_object_counts=daily_object_counts,
        selected_location=selected_location,
        cctv_locations=cctv_locations,
        pie_chart_types=pie_chart_types,
        pie_chart_counts=pie_chart_counts,
        hourly_labels=last_24_hours_labels,
        hourly_counts=hourly_detected_object_counts,
        daily_pie_chart_counts=pie_chart_counts_list,
        daily_pie_chart_types=pie_chart_types_list
    )





    

@report_bp.route('/detected-object', methods=['GET'])
@login_required
def detected_object():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Jumlah objek per halaman
    search_query = request.args.get('search_query')

    if search_query:
        detected_objects = DetectedObject.query.join(Detector).join(CCTV).join(CCTVLocation).join(Weight).join(DetectorType, Weight.detector_type_id == DetectorType.id) \
            .filter(
                db.or_(
                    DetectedObject.name.ilike(f'%{search_query}%'),
                    CCTVLocation.name.ilike(f'%{search_query}%'),
                    CCTV.type.ilike(f'%{search_query}%'),  
                    DetectorType.name.ilike(f'%{search_query}%'),
                ),
                DetectedObject.permission_id == session.get('permission_id')
            ) \
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