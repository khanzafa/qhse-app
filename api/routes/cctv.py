from flask import render_template, redirect, url_for, flash, session, Response, Blueprint, jsonify, abort
from app.models import CCTV
from app import db
from app.forms import AddCCTVForm, CCTVForm, EditCCTVForm
import cv2
import logging

from utils.auth import get_allowed_permission_ids

# Configure logging
logging.basicConfig(level=logging.DEBUG)

cctv_bp = Blueprint('cctv', __name__, url_prefix='/cctv')

# CCTV    
@cctv_bp.route('/', methods=['GET'])
@cctv_bp.route('/<int:id>', methods=['GET'])
def view(id=None):
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
        for cctv in CCTV.query.filter(CCTV.permission_id.in_(get_allowed_permission_ids())).all():
            cctvs.append({
                'id': cctv.id, 
                'location': cctv.location, 
                'type': cctv.type, 
                'ip_address': cctv.ip_address, 
                'status': cctv.status
            })        
        return jsonify(cctvs), 200

@cctv_bp.route('/', methods=['POST'])
def create():
    form = CCTVForm()    
    if form.validate_on_submit():
        cctv = CCTV(
            location=form.location.data,
            type=form.type.data, 
            ip_address=form.ip_address.data, 
            status=0, 
            role=session.get('role')
        )
        db.session.add(cctv)
        db.session.commit()
        flash('CCTV added successfully!')
        return Response(status=201)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@cctv_bp.route('/<int:id>', methods=['PUT'])
def edit(id):
    cctv = CCTV.query.get_or_404(id)
    form = CCTVForm(obj=cctv)
    if form.validate_on_submit():
        cctv.location = form.location.data
        cctv.type = form.type.data
        cctv.ip_address = form.ip_address.data
        cctv.status = form.status.data
        cctv.role = session.get('role')
        db.session.commit()
        flash('CCTV edited successfully!')
        return Response(status=204)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@cctv_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    cctv = CCTV.query.get_or_404(id)
    db.session.delete(cctv)
    db.session.commit()
    flash('CCTV deleted successfully!')
    return Response(status=204)

@cctv_bp.route('/<int:cctv_id>/stream')
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
