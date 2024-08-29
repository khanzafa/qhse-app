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

# @main.route('/')
# def index():    
#     # Read dummy data from CSV
#     cctv_data = pd.read_csv('app/static/data/data.csv')
#     graph_data = pd.read_csv('app/static/data/graphs_data.csv')

#     total_cctv = cctv_data[cctv_data['type'] == 'total_cctv']['value'].values[0]
#     active_cctv = cctv_data[cctv_data['type'] == 'active_cctv']['value'].values[0]
#     inactive_cctv = cctv_data[cctv_data['type'] == 'inactive_cctv']['value'].values[0]

#     # Generate Bar Chart for PPE Undetected
#     fig1 = go.Figure()
#     fig1.add_trace(go.Bar(
#         x=graph_data['date'],
#         y=graph_data['ppe_undetected'],
#         name='PPE Undetected'
#     ))
#     fig1.update_layout(title='PPE Undetected Per Day in One Week',
#                        xaxis_title='Date',
#                        yaxis_title='Count')
    
#     # Convert Plotly graph to Base64 image
#     img1 = pio.to_image(fig1, format='png')
#     buffer1 = io.BytesIO(img1)
#     graph1 = base64.b64encode(buffer1.getvalue()).decode()

#     # Generate Pie Chart for PPE Detection Categories
#     categories = graph_data[['no_helmet', 'no_vest', 'no_boots']].sum()
#     fig2 = go.Figure()
#     fig2.add_trace(go.Pie(
#         labels=categories.index,
#         values=categories.values,
#         hole=0.3
#     ))
#     fig2.update_layout(title='PPE Detection Categories')

#     # Convert Plotly graph to Base64 image
#     img2 = pio.to_image(fig2, format='png')
#     buffer2 = io.BytesIO(img2)
#     graph2 = base64.b64encode(buffer2.getvalue()).decode()
    
    
#  # Generate Bar Chart for Gesture Warning Detected
#     fig3 = go.Figure()
#     fig3.add_trace(go.Bar(
#         x=graph_data['gesture_warning_location'].value_counts().index,
#         y=graph_data['gesture_warning_location'].value_counts().values,
#         name='Gesture Warning Detected',
#         marker=dict(color='greenyellow')  # Change the bar color here
#     ))
#     fig3.update_layout(title='Gesture Warning Detected Per Location',
#                        xaxis_title='Location',
#                        yaxis_title='Count')
    
#     # Convert Plotly graph to Base64 image
#     img3 = pio.to_image(fig3, format='png')
#     buffer3 = io.BytesIO(img3)
#     graph3 = base64.b64encode(buffer3.getvalue()).decode()
    
#      # Generate Horizontal Bar Chart for Drowsiness Warning
#     fig4 = go.Figure()
#     fig4.add_trace(go.Bar(
#         x=graph_data['drowsiness_warning'],
#         y=graph_data['date'],
#         orientation='h',  # Horizontal bars
#         name='Drowsiness Warning Detected',
#         marker=dict(color='purple')  # Optional: Set color
#     ))
#     fig4.update_layout(title='Drowsiness Warning Detected Per Day in One Week',
#                        xaxis_title='Count',
#                        yaxis_title='Date')

#     # Convert Plotly graph to Base64 image
#     img4 = pio.to_image(fig4, format='png')
#     buffer4 = io.BytesIO(img4)
#     graph4 = base64.b64encode(buffer4.getvalue()).decode()


#     return render_template('dashboard.html', 
#                            total_cctv=total_cctv, 
#                            active_cctv=active_cctv, 
#                            inactive_cctv=inactive_cctv, 
#                            graph1=graph1, 
#                            graph2=graph2,
#                            graph3=graph3,
#                            graph4=graph4)

@main.route('/')
@login_required
def index():
    # Fetching data
    num_cctv = Camera.query.count()
    num_detectors = Detector.query.count()

    # Assuming 'name' field in DetectedObject indicates no PPE
    # Count "No helmet" violations
    num_no_helmet = DetectedObject.query.filter(DetectedObject.name.like('%No helmet%')).count()
    # Count "No vest" violations
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
    camera = Camera.query.get_or_404(detector.camera_id)
    detector_types = {
        'PPE': ppe_detector,
        'Gesture': gesture_detector,
        'Unfocused': unfocused_detector
    }
    detector = detector_types[detector.type]
    def generate_frames():
        while True:
            if detector_id in detector.frames:
                frame = detector.frames[detector_id]
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
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