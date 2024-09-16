import cv2
import logging
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session, Response, jsonify
from app.models import CCTV, Detector, DetectorType, Weight
from app import db
from app.forms import DetectorForm
from utils.auth import get_allowed_permission_ids
from flasgger import swag_from

logging.basicConfig(level=logging.DEBUG)

detector_api_docs = {
    "view" : {
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "type": "integer",
                "required": False,
                "description": "Numeric ID of the detector to get"
            }
        ],
        "definitions": {
            "Detector": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer"
                    },
                    "cctv_id": {
                        "type": "integer"
                    },
                    "weight_id": {
                        "type": "integer"
                    },
                    "running": {
                        "type": "boolean"
                    },
                    "permission_id": {
                        "type": "string"
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "A list of detectors or a specific detector",
                "schema": {
                    "$ref": "#/definitions/Detector"
                }
            },
            "404": {
                "description": "Detector not found"
            }
        }
    },
    "create" : {
        "parameters": [
            {
                "name": "cctv_id",
                "in": "formData",
                "type": "integer",
                "required": True,
                "description": "ID of the CCTV"
            },
            {
                "name": "weight_id",
                "in": "formData",
                "type": "integer",
                "required": True,   
                "description": "ID of the weight"
            },
            {
                "name": "running",
                "in": "formData",
                "type": "boolean",
                "required": True,
                "description": "Running status of the detector"
            }
        ],
        "responses": {
            "201": {
                "description": "Detector added successfully"
            }
        }
    },
    "edit" : {
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "type": "integer",
                "required": True,
                "description": "Numeric ID of the detector to edit"
            },
            {
                "name": "cctv_id",
                "in": "formData",
                "type": "integer",
                "required": True,
                "description": "ID of the CCTV"
            },
            {
                "name": "weight_id",
                "in": "formData",
                "type": "integer",
                "required": True,
                "description": "ID of the weight"
            },
            {
                "name": "running",
                "in": "formData",
                "type": "boolean",
                "required": True,
                "description": "Running status of the detector"
            }
        ],
        "responses": {
            "200": {
                "description": "Detector updated successfully"
            }
        }
    },
    "delete" : {
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "type": "integer",
                "required": True,
                "description": "Numeric ID of the detector to delete"
            }
        ],
        "responses": {
            "204": {
                "description": "Detector deleted successfully"
            }
        }
    },
    "stream" : {
        "parameters": [
            {
                "name": "detector_id",
                "in": "path",
                "type": "integer",
                "required": True,
                "description": "Numeric ID of the detector to stream"
            }
        ],
        "responses": {
            "200": {
                "description": "Detector stream"
            }
        }
    }
}

detector_bp = Blueprint('detector', __name__, url_prefix='/detector')

# DETECTOR
@detector_bp.route('/', methods=['GET'])
@detector_bp.route('/<int:id>', methods=['GET'])
@swag_from(detector_api_docs['view'])
def view(id=None):
    if id:
        detector = Detector.query.get_or_404(id)
        detector = {
            'id': detector.id,
            'cctv_id': detector.cctv_id,
            'weight_id': detector.weight_id,
            'running': detector.running,
            'permission_id': detector.permission_id
        }
        return jsonify(detector), 200
    else:
        detectors = []
        for detector in Detector.query.filter(Detector.permission_id.in_(get_allowed_permission_ids())).all():
            detectors.append({
                'id': detector.id,
                'cctv_id': detector.cctv_id,
                'weight_id': detector.weight_id,
                'running': detector.running,
                'permission_id': detector.permission_id
            })        
        return jsonify(detectors), 200

@detector_bp.route('/', methods=['POST'])
@swag_from(detector_api_docs['create'])
def create():
    form = DetectorForm()
    if form.validate_on_submit():
        detector = Detector(
            cctv_id=form.cctv_id.data,
            weight_id=form.weight_id.data,
            running=form.running.data,
            permission_id=session.get('permission_id')
        )
        db.session.add(detector)
        db.session.commit()
        flash('Detector added successfully!')
        return Response(status=201)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@detector_bp.route('/<int:id>', methods=['PUT'])
@swag_from(detector_api_docs['edit'])
def edit(id):
    detector = Detector.query.get_or_404(id)
    form = DetectorForm(obj=detector)
    if form.validate_on_submit():
        detector.cctv_id = form.cctv_id.data
        detector.weight_id = form.weight_id.data
        detector.running = form.running.data
        db.session.commit()
        flash('Detector updated successfully!')
        return Response(status=200)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@detector_bp.route('/<int:id>', methods=['DELETE'])
@swag_from(detector_api_docs['delete'])
def delete(id):
    detector = Detector.query.get_or_404(id)
    db.session.delete(detector)
    db.session.commit()
    flash('Detector deleted successfully!')
    return Response(status=204)

@detector_bp.route('/<int:detector_id>/stream')
@swag_from(detector_api_docs['stream'])
def detector_stream(detector_id):
    detector = Detector.query.get_or_404(detector_id)    
    detector_type = detector.detector_type_id
    detector_types = {
        # 'PPE': ppe_detector,
        # 'Gesture': gesture_detector,
        # 'Unfocused': unfocused_detector
    }
    detector = detector_types[detector_type]
    def generate_frames():
        while True:
            if detector_id in detector.frames:
                print(f"Detector {detector_id} dengan tipe {detector_type} terdapat frame")
                frame = detector.frames[detector_id]            
                print("Frame:", frame)
                # cv2.imshow("Frame", frame)
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'   
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                print(f"Detector {detector_id} dengan tipe {detector_type} TIDAK terdapat frame")
                continue
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
