import cv2
import requests
from flask import Blueprint, render_template, flash, redirect, request, url_for, Response, stream_with_context, abort, jsonify
from app.extensions import db
from app.models import Camera, Contact, DetectedObject, Detector
from app.forms import AddCCTVForm, EditCCTVForm, SelectCCTVForm, ContactForm, DetectorForm    
from app import detector

main = Blueprint('main', __name__)
current_user = {'name': 'John'}

@main.route('/')
def index():    
    return render_template('dashboard.html', current_user=current_user)

@main.route('/cctv/view_feed/<int:camera_id>')
def view_cctv_feed(camera_id):
    return render_template('view_cctv_feed.html', title='Live CCTV Feed', camera_id=camera_id, current_user=current_user)

@main.route('/cctv/stream/<int:camera_id>')
def stream(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    mode = request.args.get('mode', 'normal')
    def generate_frames():
        if mode == 'annotated':
            while True:
                if camera_id in detector.frames:
                    frame = detector.frames[camera_id]
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                else:
                    continue
        else:
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
        return redirect(url_for('manage_cctv'))
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
    return redirect(url_for('manage_cctv'))

@main.route('/detector/manage', methods=['GET', 'POST'])
@main.route('/detector/manage/<int:id>', methods=['GET', 'POST'])
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

@main.route('/detector/delete/<int:id>')
def delete_detector(id):
    detector = Detector.query.get_or_404(id)
    db.session.delete(detector)
    db.session.commit()
    flash('Detector entry deleted successfully!')
    return redirect(url_for('main.manage_detector'))

@main.route('/contact/manage', methods=['GET', 'POST'])
@main.route('/contact/manage/<int:id>', methods=['GET', 'POST'])
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

@main.route('/contact/delete/<int:id>')
def delete_contact(id):
    contact = Contact.query.get_or_404(id)
    db.session.delete(contact)
    db.session.commit()
    flash('Contact entry deleted successfully!')
    return redirect(url_for('main.manage_contact'))