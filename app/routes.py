import base64
import io
import cv2
import pandas as pd
# import plotly.graph_objects as go
# import plotly.io as pio
import requests
from datetime import datetime, timedelta
from collections import Counter
from flask import Blueprint, render_template, flash, redirect, request, url_for, Response, stream_with_context, abort, jsonify
from app.extensions import db
from app.models import Camera, Contact, DetectedObject, Detector, User
from app.forms import AddCCTVForm, EditCCTVForm, SelectCCTVForm, ContactForm, DetectorForm, LoginForm, RegistrationForm 
from app import gesture_detector, ppe_detector, unfocused_detector
from flask_login import current_user, login_user, logout_user, login_required

main = Blueprint('main', __name__)
current_user = {'name': 'John'}
GRAPHICS_DIR = 'app/static/graphics'

@main.route('/')
def index():
    return render_template('index.html', title='Home', current_user=current_user)

@main.route('/report/dashboard')
@login_required
def dashboard():
    # Fetching data
    num_cctv = Camera.query.count()
    num_detectors = Detector.query.count()

    num_no_helmet = DetectedObject.query.filter(DetectedObject.name.like('%No helmet%')).count()
    num_no_vest = DetectedObject.query.filter(DetectedObject.name.like('%No vest%')).count()
    num_no_ppe = num_no_helmet + num_no_vest
    num_reckless = DetectedObject.query.filter(DetectedObject.name == 'sleepy').count()
    num_gesture_help = DetectedObject.query.filter(DetectedObject.name == 'cross-hands').count()

    # Example data for charts (this would normally be queried from the database)
    today = datetime.today()
    last_7_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    chatbot_requests = Counter({day: 0 for day in last_7_days})  # Replace with actual data
    safety_incidents = Counter({day: 0 for day in last_7_days})  # Replace with actual data

    return render_template('dashboard.html', num_cctv=num_cctv, num_detectors=num_detectors,
                           num_no_ppe=num_no_ppe, num_reckless=num_reckless, num_gesture_help=num_gesture_help,
                           chatbot_requests=chatbot_requests, safety_incidents=safety_incidents)

@main.route('/cctv/view_feed/<int:camera_id>')
def view_cctv_feed(camera_id):
    return render_template('view_cctv_feed.html', title='Live CCTV Feed', camera_id=camera_id, current_user=current_user)

@main.route('/cctv/stream/<int:camera_id>')
def cctv_stream(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    def generate_frames():
        address = 0 if camera.ip_address == "http://0.0.0.0" else camera.ip_address            
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

@main.route('/detector/view_feed/<int:detector_id>')
def view_detector_feed(detector_id):
    return render_template('view_detector_feed.html', title='Live Detector Feed', detector_id=detector_id, current_user=current_user)

@main.route('/detector/stream/<int:detector_id>')
def detector_stream(detector_id):
    detector = Detector.query.get_or_404(detector_id)    
    detector_type = detector.type
    detector_types = {
        'PPE': ppe_detector,
        'Gesture': gesture_detector,
        'Unfocused': unfocused_detector
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

@main.route('/cctv/all', methods=['GET'])
def view_all_cctv():
    cameras = Camera.query.all()
    return jsonify([camera.to_dict() for camera in cameras])

@main.route('/cctv/manage', methods=['GET', 'POST'])
def manage_cctv():
    form = AddCCTVForm()    
    if form.validate_on_submit():
        camera = Camera(location=form.location.data, ip_address=form.ip_address.data, status=0)
        db.session.add(camera)
        db.session.commit()
        flash('CCTV added successfully!')
        return redirect(url_for('main.manage_cctv'))
    cameras = Camera.query.all()
    return render_template('manage_cctv.html', title='Manage CCTV', current_user=current_user, form=form, cameras=cameras)

@main.route('/cctv/edit/<int:id>', methods=['GET', 'POST'])
def edit_cctv(id):
    camera = Camera.query.get_or_404(id)
    form = EditCCTVForm(obj=camera)
    if form.validate_on_submit():
        camera.location = form.location.data
        camera.type = form.type.data
        camera.ip_address = form.ip_address.data
        camera.status = form.status.data
        db.session.commit()
        flash('CCTV updated successfully!')
        return redirect(url_for('main.manage_cctv'))
    return render_template('edit_cctv.html', title='Edit CCTV', form=form, current_user=current_user)

@main.route('/cctv/delete/<int:id>', methods=['POST'])
def delete_cctv(id):
    camera = Camera.query.get_or_404(id)
    db.session.delete(camera)
    db.session.commit()
    flash('CCTV deleted successfully!', 'success')
    return redirect(url_for('main.manage_cctv'))

@main.route('/object-detection/detector/manage', methods=['GET', 'POST'])
@main.route('/object-detection/detector/manage/<int:id>', methods=['GET', 'POST'])
def manage_detector(id=None):
    if id:
        detector = Detector.query.get_or_404(id)
        form = DetectorForm(obj=detector)
        title = "Edit Detector"
    else:
        detector = None
        form = DetectorForm()
        title = "Add New Detector"

    cameras = Camera.query.all()
    form.camera_id.choices = [(camera.id, camera.location) for camera in cameras]

    if form.validate_on_submit():
        if detector:
            detector.camera_id = form.camera_id.data
            detector.type = form.type.data
            detector.running = form.running.data
        else:
            new_detector = Detector(
                camera_id=form.camera_id.data,
                type=form.type.data,
                running=form.running.data
            )
            db.session.add(new_detector)
        
        db.session.commit()
        flash('Detector entry updated successfully!' if detector else 'Detector entry added successfully!')
        return redirect(url_for('main.manage_detector'))
    
    detectors = Detector.query.all()
    return render_template('manage_detector.html', form=form, detectors=detectors, detector=detector, title=title)

@main.route('/object-detection/detector/delete/<int:id>')
def delete_detector(id):
    detector = Detector.query.get_or_404(id)
    db.session.delete(detector)
    db.session.commit()
    flash('Detector entry deleted successfully!')
    return redirect(url_for('main.manage_detector'))

@main.route('/object-detection/contact/manage', methods=['GET', 'POST'])
@main.route('/object-detection/contact/manage/<int:id>', methods=['GET', 'POST'])
def manage_contact(id=None):
    if id:
        contact = Contact.query.get_or_404(id)
        form = ContactForm(obj=contact)
        title = "Edit Contact"
    else:
        contact = None
        form = ContactForm()
        title = "Add New Contact"

    if form.validate_on_submit():
        if contact:
            contact.phone_number = form.phone_number.data
            contact.name = form.name.data  # Ganti 'description' dengan 'name'
        else:
            new_contact = Contact(
                phone_number=form.phone_number.data, 
                name=form.name.data
            )
            db.session.add(new_contact)
        
        db.session.commit()
        flash('Contact entry updated successfully!' if contact else 'Contact entry added successfully!')
        return redirect(url_for('main.manage_contact'))
    
    whas = Contact.query.all()
    return render_template('manage_contact.html', form=form, whas=whas, contact=contact, title=title)

@main.route('/object-detection/contact/delete/<int:id>')
def delete_contact(id):
    contact = Contact.query.get_or_404(id)
    db.session.delete(contact)
    db.session.commit()
    flash('Contact entry deleted successfully!')
    return redirect(url_for('main.manage_contact'))

# Manage model
@main.route('/object-detection/model/manage', methods=['GET', 'POST'])
@main.route('/object-detection/model/manage/<int:id>', methods=['GET', 'POST'])
def manage_model(id=None):
    return render_template('manage_model.html', title='Manage Model', current_user=current_user)
    
# Manage message
@main.route('/object-detection/message/manage', methods=['GET', 'POST'])
@main.route('/object-detection/message/manage/<int:id>', methods=['GET', 'POST'])
def manage_message(id=None):
    return render_template('manage_message.html', title='Manage Message', current_user=current_user)

@main.route('/report/detected-object', methods=['GET'])
def detected_object():
    detected_objects = DetectedObject.query.join(Detector).filter(Detector.type == 'PPE').order_by(DetectedObject.timestamp.desc()).all()
    return render_template('ppe/index.html', detected_objects=detected_objects)

@main.route('/report/detected-object/view-object/<int:object_id>', methods=['GET'])
def view_object(object_id):
    detected_object = DetectedObject.query.get_or_404(object_id)    
    return render_template('ppe/view_object.html', detected_object=detected_object)
