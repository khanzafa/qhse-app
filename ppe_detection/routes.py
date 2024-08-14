import cv2
import requests
from flask import Blueprint, render_template, flash, redirect, request, url_for, Response, stream_with_context, abort, jsonify
from app.extensions import db
from app.models import Camera, DetectedObject, Detector
from app.forms import DetectorForm

ppe = Blueprint('ppe', __name__)

# Data dummy
detected_objects = [
    {
        'id': 1,
        'detector_id': 1,
        'name': 'Person',
        'frame': b'',
        'timestamp': '2021-09-01 08:00:00'
    },
    {
        'id': 2,
        'detector_id': 2,
        'name': 'Person',
        'frame': b'',
        'timestamp': '2021-09-01 08:00:00'
    }
]

@ppe.route('/ppe-detection', methods=['GET'])
def ppe_detection():
    # query by type
    detected_objects = DetectedObject.query.order_by(DetectedObject.timestamp.desc()).all()
    return render_template('ppe/index.html', detected_objects=detected_objects)

@ppe.route('/ppe-detection/view-object/<int:object_id>', methods=['GET'])
def view_object(object_id):
    detected_object = DetectedObject.query.get_or_404(object_id)    
    # detected_object = next((object for object in detected_objects if object['id'] == object_id), None)
    return render_template('ppe/view_object.html', detected_object=detected_object)