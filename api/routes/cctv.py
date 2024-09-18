from flask import render_template, redirect, url_for, flash, session, Response, Blueprint, jsonify, abort
from app.models import CCTV
from app import db
from app.forms import AddCCTVForm, CCTVForm, EditCCTVForm
import cv2
import logging
from flasgger import swag_from

from utils.auth import get_allowed_permission_ids

# Configure logging
logging.basicConfig(level=logging.DEBUG)

cctv_api_docs = {
    "view" : {
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "type": "integer",
                "required": False,
                "description": "Numeric ID of the CCTV to get"
            }
        ],
        "definitions": {
            "CCTV": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer"
                    },
                    "location": {
                        "type": "string"
                    },
                    "type": {
                        "type": "string"
                    },
                    "ip_address": {
                        "type": "string"
                    },
                    "status": {
                        "type": "integer"
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "A list of CCTVs or a specific CCTV",
                "schema": {
                    "$ref": "#/definitions/CCTV"
                }
            },
            "404": {
                "description": "CCTV not found"
            }
        }
    },
    "create" : {
        "parameters": [
            {
                "name": "location",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Location of the CCTV"
            },
            {
                "name": "type",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Type of the CCTV"
            },
            {
                "name": "ip_address",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "IP address of the CCTV"
            }
        ],
        "responses": {
            "201": {
                "description": "CCTV added successfully"
            },
            "400": {
                "description": "Form validation failed"
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
                "description": "Numeric ID of the CCTV to edit"
            }
        ],
        "responses": {
            "200": {
                "description": "CCTV edited successfully"
            },
            "400": {
                "description": "Form validation failed"
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
                "description": "Numeric ID of the CCTV to delete"
            }
        ],
        "responses": {
            "200": {
                "description": "CCTV deleted successfully"
            }
        }
    },
    "stream" : {
        "parameters": [
            {
                "name": "cctv_id",
                "in": "path",
                "type": "integer",
                "required": True,
                "description": "Numeric ID of the CCTV to stream"
            }
        ],
        "responses": {
            "200": {
                "description": "CCTV stream"
            }
        }
    }
}

cctv_bp = Blueprint('cctv', __name__, url_prefix='/cctv')

# CCTV    
@cctv_bp.route('/', methods=['GET'])
@cctv_bp.route('/<int:id>', methods=['GET'])
@swag_from(cctv_api_docs['view'])
def view(id=None):
    logging.debug(f"Permission ID: {session.get('permission_id')}")
    form = CCTVForm()    
    if id:
        cctv = CCTV.query.get_or_404(id)
        cctv = {
            'id': cctv.id,
            'location': cctv.location,
            'type': cctv.type,
            'ip_address': cctv.ip_address,
            'status': cctv.status
        }
        return jsonify(cctv), 200             
    else:
        cctvs = []
        for cctv in CCTV.query.filter(CCTV.permission_id == session.get('permission_id')).all():
            cctvs.append({
                'id': cctv.id, 
                'location': cctv.location, 
                'type': cctv.type, 
                'ip_address': cctv.ip_address, 
                'status': cctv.status
            })        
        # return jsonify(cctvs), 200
        return render_template('manage_cctv.html', cameras=cctvs, form=form)

@cctv_bp.route('/', methods=['POST'])
@swag_from(cctv_api_docs['create'])
def create():
    form = CCTVForm()    
    if form.validate_on_submit():
        cctv = CCTV(
            location=form.location.data,
            type=form.type.data, 
            ip_address=form.ip_address.data, 
            status=0, 
            permission_id=session.get('permission_id')
        )
        db.session.add(cctv)
        db.session.commit()
        flash('CCTV added successfully!')
        # return Response(status=201)
        return redirect(url_for('cctv.view'))
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@cctv_bp.route('/<int:id>/edit', methods=['POST'])
@swag_from(cctv_api_docs['edit'])
def edit(id):
    cctv = CCTV.query.get_or_404(id)
    form = CCTVForm(obj=cctv)
    logging.debug(f"Form data: {form.data}")
    if form.validate_on_submit():
        logging.debug(f"Form validated: {form.data}")
        cctv.location = form.location.data
        cctv.type = form.type.data
        cctv.ip_address = form.ip_address.data
        cctv.status = form.status.data
        cctv.permission_id = session.get('permission_id')
        db.session.commit()
        flash('CCTV edited successfully!')
        # return Response(status=204)
        return redirect(url_for('cctv.view'))
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@cctv_bp.route('/<int:id>/delete', methods=['POST'])
@swag_from(cctv_api_docs['delete'])
def delete(id):
    logging.debug(f"Deleting CCTV with ID: {id}")
    cctv = CCTV.query.get_or_404(id)
    db.session.delete(cctv)
    db.session.commit()
    flash('CCTV deleted successfully!')
    # return Response(status=204)
    return redirect(url_for('cctv.view'))

@cctv_bp.route('/<int:cctv_id>/stream')
@swag_from(cctv_api_docs['stream'])
def stream(cctv_id):
    cctv = CCTV.query.get_or_404(cctv_id)
    def generate_frames():
        address = 0 if cctv.ip_address == "http://0.0.0.0" else cctv.ip_address            
        cap = cv2.VideoCapture(address)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
