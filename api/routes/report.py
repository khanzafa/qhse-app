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
# @login_required
def dashboard():
    # Fetching data
    num_cctv = CCTV.query.count()
    num_detectors = Detector.query.count()

    num_no_helmet = DetectedObject.query.filter(
        DetectedObject.name.like("%No helmet%")
    ).count()
    num_no_vest = DetectedObject.query.filter(
        DetectedObject.name.like("%No vest%")
    ).count()
    num_no_ppe = num_no_helmet + num_no_vest
    num_reckless = DetectedObject.query.filter(DetectedObject.name == "sleepy").count()
    num_gesture_help = DetectedObject.query.filter(
        DetectedObject.name == "cross-hands"
    ).count()

    # Example data for charts (this would normally be queried from the database)
    today = datetime.today()
    last_7_days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    chatbot_requests = Counter(
        {day: 0 for day in last_7_days}
    )  # Replace with actual data
    safety_incidents = Counter(
        {day: 0 for day in last_7_days}
    )  # Replace with actual data
    
    data = {
        "num_cctv": num_cctv,
        "num_detectors": num_detectors,
        "num_no_ppe": num_no_ppe,
        "num_reckless": num_reckless,
        "num_gesture_help": num_gesture_help,
        "chatbot_requests": chatbot_requests,
        "safety_incidents": safety_incidents
    }
    
    return jsonify(data), 200 
    

@report_bp.route("/detected-object", methods=["GET"])
@report_bp.route("/detected-object/<int:object_id>", methods=["GET"])
def detected(object_id=None):
    if object_id is not None:
        detected_object = (
            DetectedObject.query
            .options(joinedload(DetectedObject.detector).joinedload(Detector.detector_type))
            .get_or_404(object_id)
        )
        
        detected_object_data = {
            "id": detected_object.id,
            "name": detected_object.name,
            "detector": detected_object.detector.detector_type.name if detected_object.detector and detected_object.detector.detector_type else None,  # Handle potential None values
            "detector_id": detected_object.detector_id,
            "frame": detected_object.frame.hex() if detected_object.frame else None,  # Convert binary data to a hex string
            "timestamp": detected_object.timestamp.isoformat(),  # Convert datetime to ISO 8601 string
            "permission": detected_object.permission.name if detected_object.permission else None,  # Handle relationship to Permission model
            "permission_id": detected_object.permission_id,
            "created_at": detected_object.created_at.isoformat(),  # Convert datetime to ISO 8601 string
            "updated_at": detected_object.updated_at.isoformat(),  # Convert datetime to ISO 8601 string
        }
        return jsonify(detected_object_data), 200
    else:
        page = request.args.get("page", 1, type=int)
        per_page = 10  # Jumlah objek per halaman
        search_query = request.args.get("search_query")

        if search_query:
            detected_objects = (
                DetectedObject.query.join(Detector)
                .join(CCTV)
                .join(Detector.detector_type)
                .filter(DetectedObject.name.like(f"%{search_query}%"))
                .order_by(DetectedObject.timestamp.desc())
                .paginate(page=page, per_page=per_page)
            )
        else:
            detected_objects = (
                DetectedObject.query.join(Detector)
                .join(CCTV)
                .order_by(DetectedObject.timestamp.desc())
                .paginate(page=page, per_page=per_page)
            )
            
        detected_objects_data = [
            {
                "id": obj.id,
                "name": obj.name,
                "detector": obj.detector.detector_type.name if obj.detector and obj.detector.detector_type else None,  # Handle potential None values
                "detector_id": obj.detector_id,
                "frame": obj.frame.hex() if obj.frame else None,  # Convert binary data to a hex string
                "timestamp": obj.timestamp.isoformat(),  # Convert datetime to ISO 8601 string
                "permission": obj.permission.name if obj.permission else None,  # Handle relationship to Permission model
                "permission_id": obj.permission_id,
                "created_at": obj.created_at.isoformat(),  # Convert datetime to ISO 8601 string
                "updated_at": obj.updated_at.isoformat(),  # Convert datetime to ISO 8601 string
            }
            for obj in detected_objects.items
        ]
        
        pagination_info = {
            "total_pages": detected_objects.pages,
            "current_page": detected_objects.page,
            "per_page": detected_objects.per_page,
            "total_items": detected_objects.total,
        }
        
        return jsonify(
            {
                "detected_objects": detected_objects_data,
                "pagination": pagination_info,
                "search_query": search_query,
            }
        ), 200