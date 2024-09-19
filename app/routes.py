import base64
import io
import os
import re
import cv2
import pandas as pd

# import plotly.graph_objects as go
# import plotly.io as pio
import requests
from datetime import datetime, timedelta
from collections import Counter
from flask import (
    Blueprint,
    render_template,
    flash,
    redirect,
    request,
    send_from_directory,
    session,
    url_for,
    Response,
    stream_with_context,
    abort,
    jsonify,
)
from app.extensions import db
from app.models import (
    CCTV,
    Contact,
    DetectedObject,
    Detector,
    DetectorType,
    MessageTemplate,
    NotificationRule,
    Permission,
    User,
    UserPermission,
    Weight,
    suMenu,
)
from app.forms import (
    AccessForm,
    AddCCTVForm,
    EditCCTVForm,
    MessageTemplateForm,
    ModelForm,
    NotificationRuleForm,
    SelectCCTVForm,
    ContactForm,
    DetectorForm,
    LoginForm,
    RegistrationForm,
)
# from app import gesture_detector, ppe_detector, unfocused_detector
from flask_login import current_user, login_user, logout_user, login_required
import logging

from utils.auth import get_allowed_permission_ids

main = Blueprint("main", __name__)
# current_user = {'name': 'John'}
GRAPHICS_DIR = "app/static/graphics"


@main.route("/", methods=["GET"])
def index():    
    # Get the permission IDs for the current user
    allowed_permission_ids = get_allowed_permission_ids()    
    
    # Query the suMenu model for menus associated with those permission IDs
    menus = suMenu.query.filter(suMenu.permission_id.in_(allowed_permission_ids)).all()
    
    # Render the index template and pass the menu data
    return render_template("index.html", menus=menus)

@main.route('/report/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    session_permission = session.get('permission_id')

    # Agregasi data terkait jumlah CCTV, detektor, dan PPE
    num_cctv = CCTV.query.filter(CCTV.permission_id == session.get('permission_id')).count()
    num_detectors = Detector.query.filter(Detector.permission_id == session.get('permission_id')).count()

    num_no_helmet = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "no-helmet").count()
    num_no_vest = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "no-vest").count()
    num_no_ppe = num_no_helmet + num_no_vest
    num_drowsy = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "drowsy").count()
    num_phone = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "phone").count()
    num_no_seatbelt = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "no-seatbelt").count()
    num_reckless = num_drowsy + num_phone + num_no_seatbelt
    num_danger = DetectedObject.query.filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == "cross-hand").count()
    
    # Ambil semua kamera
    results = db.session.query(DetectedObject, CCTV).select_from(DetectedObject) \
        .join(Detector) \
        .join(CCTV) \
        .all()

    # Buat dictionary kamera
    cameras = {camera.id: camera.location for obj, camera in results}
    cameras = {'all': f"All Cameras", **cameras}

    # Dapatkan kamera yang dipilih dari form atau set 'all' sebagai default
    selected_camera_ppe = request.form.get('camera', 'all')
    selected_camera_driver = request.form.get('camera', 'all')
    selected_camera_danger = request.form.get('camera', 'all')
    
    
    # Filter data berdasarkan kamera yang dipilih
    if selected_camera_ppe == 'all':
        # Mengambil semua data untuk semua kamera
        total_no_helmet_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'no-helmet').count()
        total_no_vest_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'no-vest').count()
    else:
        # Mengambil data berdasarkan kamera yang dipilih
        data = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'),CCTV.id == selected_camera_ppe).all()

        total_no_helmet_all = sum(1 for obj in data if obj.name == 'no-helmet')
        total_no_vest_all = sum(1 for obj in data if obj.name == 'no-vest')
            
    
    # Filter data berdasarkan kamera yang dipilih
    if selected_camera_driver == 'all':
        # Mengambil semua data untuk semua kamera
        total_drowsy_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'drowsy').count()
        total_no_seatbelt_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'no-seatbelt').count()
        total_phone_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'phone').count()
        total_reckless_all = total_drowsy_all + total_no_seatbelt_all + total_phone_all
    else:
        # Mengambil data berdasarkan kamera yang dipilih
        data = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_driver).all()

        total_drowsy_all = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_driver, DetectedObject.name == 'drowsy').count()
        total_no_seatbelt_all = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_driver, DetectedObject.name == 'no-seatbelt').count()
        total_phone_all = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_driver, DetectedObject.name == 'phone').count()
        total_reckless_all = total_drowsy_all + total_no_seatbelt_all + total_phone_all
            
            
    # Filter data berdasarkan kamera yang dipilih
    if selected_camera_danger == 'all':
        # Mengambil semua data untuk semua kamera
        total_gesture_help_all = db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), DetectedObject.name == 'cross-hand').count()
    else:
        # Mengambil data berdasarkan kamera yang dipilih
        data = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_danger).all()
        total_gesture_help_all = db.session.query(DetectedObject).join(Detector).join(CCTV) \
            .filter(DetectedObject.permission_id == session.get('permission_id'), CCTV.id == selected_camera_danger, DetectedObject.name == 'cross-hand').count()

    # Ambil tanggal terbaru dan terawal dari data
    latest_entry = DetectedObject.query.order_by(DetectedObject.timestamp.desc()).first()
    if latest_entry:
        latest_date = latest_entry.timestamp
    else:
        latest_date = datetime.utcnow()

    earliest_date = latest_date - timedelta(days=7)

        # Example data for PPE detection per day
    today = datetime.today()
    last_7_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    
    # Buat array untuk data harian
    num_no_vest_per_day = []
    num_no_helmet_per_day = []
    num_drowsy_per_day = []
    num_phone_per_day = []
    num_no_seatbelt_per_day = []
    num_danger_per_day = []


    # Fetch daily counts for no-vest and no-helmet
    if selected_camera_ppe == 'all':
        num_no_vest_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-vest',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

        num_no_helmet_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-helmet',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
    else:
        num_no_vest_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-vest',
                CCTV.id == selected_camera_ppe,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

        num_no_helmet_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-helmet',
                CCTV.id == selected_camera_ppe,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]


    # Fetch daily counts for driver
    if selected_camera_driver == 'all':
        num_drowsy_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'drowsy',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

        num_phone_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'phone',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
        
        num_no_seatbelt_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-seatbelt',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
                
    else:
        num_drowsy_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'drowsy',
                CCTV.id == selected_camera_driver,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

        num_phone_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'phone',
                CCTV.id == selected_camera_driver,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
        
        num_no_seatbelt_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'no-seatbelt',
                CCTV.id == selected_camera_driver,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

    # Fetch daily counts for danger
    if selected_camera_driver == 'all':
        num_danger_per_day = [
            db.session.query(DetectedObject).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'cross-hand',
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]
    else:
        num_danger_per_day = [
            db.session.query(DetectedObject).join(Detector).join(CCTV).filter(DetectedObject.permission_id == session.get('permission_id'), 
                DetectedObject.name == 'cross-hand',
                CCTV.id == selected_camera_danger,
                DetectedObject.timestamp.between(latest_date - timedelta(days=i+1), latest_date - timedelta(days=i))
            ).count() for i in range(7)
        ]

    # Hitung total harian untuk menampilkan di template
    total_no_vest = sum(num_no_vest_per_day) or 0
    total_no_helmet = sum(num_no_helmet_per_day) or 0
    total_no_ppe = sum(num_no_helmet_per_day + num_no_vest_per_day)
    total_drowsy = sum(num_drowsy_per_day) or 0
    total_phone = sum(num_phone_per_day) or 0
    total_no_seatbelt = sum(num_no_seatbelt_per_day) or 0
    total_reckless_driver = sum(num_drowsy_per_day + num_phone_per_day + num_no_seatbelt_per_day) or 0
    total_danger = sum(num_danger_per_day) or 0


    # Render data ke template dashboard
    return render_template(
        'dashboard.html',
        cameras=cameras,
        selected_camera_ppe=selected_camera_ppe,
        selected_camera_driver=selected_camera_driver,
        selected_camera_danger=selected_camera_danger,
        num_cctv=num_cctv,
        num_detectors=num_detectors,
        num_no_ppe=num_no_ppe,
        num_no_helmet=total_no_helmet_all,
        num_no_vest=num_no_vest,
        num_drowsy=total_drowsy_all,
        num_no_seatbelt=total_no_seatbelt_all,
        num_phone=total_phone_all,
        num_reckless=num_reckless,
        num_danger=num_danger,
        last_7_days=last_7_days,
        num_no_vest_per_day=num_no_vest_per_day,
        num_no_helmet_per_day=num_no_helmet_per_day,
        num_drowsy_per_day=num_drowsy_per_day,
        num_phone_per_day=num_phone_per_day,
        num_no_seatbelt_per_day=num_no_seatbelt_per_day,
        num_danger_per_day=num_danger_per_day,
    )

# DASHBOARD DUMMY
# @main.route('/report/dashboard')
# @login_required
# def dashboard():
#     # Fetching data
#     num_cctv = CCTV.query.count()
#     num_detectors = Detector.query.count()

#     # Dummy data for PPE detection per camera
#     cameras = [
#         {"camera_id": "CAM001", "camera_name": "Camera 1"},
#         {"camera_id": "CAM002", "camera_name": "Camera 2"},
#         {"camera_id": "CAM003", "camera_name": "Camera 3"},
#         {"camera_id": "CAM004", "camera_name": "Camera 4"},
#         {"camera_id": "CAM005", "camera_name": "Camera 5"}
#     ]

#     # Example data for PPE detection per day
#     today = datetime.today()
#     last_7_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

#     # Create a list to store camera data
#     camera_data = []
#     for camera in cameras:
#         data = [
#             {"date": date, "no_helmet": 10 * (i + 1), "no_vest": 5 * (i + 1)}
#             for i, date in enumerate(last_7_days)
#         ]
#         camera_data.append({"camera_id": camera["camera_id"], "data": data})

#     # Calculate totals for pie chart
#     total_no_helmet = sum(entry["no_helmet"] for camera in camera_data for entry in camera["data"])
#     total_no_vest = sum(entry["no_vest"] for camera in camera_data for entry in camera["data"])

#     # Combine data for pie chart and bar chart
#     ppe_detection_data = {
#         "dates": last_7_days,
#         "camera_data": camera_data,
#         "total_no_helmet": total_no_helmet,
#         "total_no_vest": total_no_vest
#     }

#     return render_template('dashboard.html', num_cctv=num_cctv, num_detectors=num_detectors,
#                            ppe_detection_data=ppe_detection_data)

# DONE
# @main.route("/cctv/view_feed/<int:camera_id>")
# def view_cctv_feed(camera_id):
#     return render_template(
#         "view_cctv_feed.html",
#         title="Live CCTV Feed",
#         camera_id=camera_id,
#         current_user=current_user,
#     )


# @main.route("/object-detection/detector/delete/<int:id>")
# def delete_detector(id):
#     detector = Detector.query.get_or_404(id)
#     db.session.delete(detector)
#     db.session.commit()
#     flash("Detector entry deleted successfully!")
#     return redirect(url_for("main.manage_detector"))


# @main.route("/object-detection/contact/manage", methods=["GET", "POST"])
# @main.route("/object-detection/contact/manage/<int:id>", methods=["GET", "POST"])
# def manage_contact(id=None):
#     if id:
#         contact = Contact.query.get_or_404(id)
#         form = ContactForm(obj=contact)
#         title = "Edit Contact"
#     else:
#         contact = None
#         form = ContactForm()
#         title = "Add New Contact"

#     if form.validate_on_submit():
#         if contact:
#             contact.phone_number = form.phone_number.data
#             contact.name = form.name.data  # Ganti 'description' dengan 'name'
#         else:
#             new_contact = Contact(
#                 phone_number=form.phone_number.data, name=form.name.data
#             )
#             db.session.add(new_contact)

#         db.session.commit()
#         flash(
#             "Contact entry updated successfully!"
#             if contact
#             else "Contact entry added successfully!"
#         )
#         return redirect(url_for("main.manage_contact"))

#     whas = Contact.query.all()
#     return render_template(
#         "manage_contact.html", form=form, whas=whas, contact=contact, title=title
#     )


# @main.route("/object-detection/contact/delete/<int:id>")
# def delete_contact(id):
#     contact = Contact.query.get_or_404(id)
#     db.session.delete(contact)
#     db.session.commit()
#     flash("Contact entry deleted successfully!")
#     return redirect(url_for("main.manage_contact"))

# # DONE
# # Manage model
# @main.route("/object-detection/model/manage", methods=["GET", "POST"])
# @main.route("/object-detection/model/manage/<int:id>", methods=["GET", "POST"])
# def manage_model(id=None):
#     if id:
#         model = Weight.query.get_or_404(id)
#         form = ModelForm(obj=model)
#         title = "Edit Model"
#     else:
#         model = None
#         form = ModelForm()
#         title = "Add New Model"

#     detector_types = DetectorType.query.all()
#     form.detector_type.choices = [
#         (detector_type.id, detector_type.name) for detector_type in detector_types
#     ]

#     weights_dir = "weights"
#     if form.validate_on_submit():
#         print("Model:", model)
#         if model:
#             model.name = form.name.data
#         else:
#             form.file.data.save(os.path.join(weights_dir, form.file.data.filename))
#             new_model = Weight(
#                 name=form.name.data,
#                 detector_type_id=form.detector_type.data,
#                 file=form.file.data.read(),
#                 path=os.path.join(weights_dir, form.file.data.filename),
#                 created_at=datetime.now(),
#             )
#             db.session.add(new_model)

#         db.session.commit()
#         flash(
#             "Model entry updated successfully!"
#             if model
#             else "Model entry added successfully!"
#         )
#         return redirect(url_for("main.manage_model"))

#     models = Weight.query.all()
#     return render_template(
#         "manage_model.html", form=form, models=models, model=model, title=title
#     )

# # DONE
# @main.route("/object-detection/model/delete/<int:id>", methods=["POST"])
# def delete_model(id):
#     model = Weight.query.get_or_404(id)
#     db.session.delete(model)
#     db.session.commit()
#     flash("Model deleted successfully!")
#     return redirect(url_for("main.manage_model"))

# # DONE
# # Manage message
# @main.route("/object-detection/message/manage", methods=["GET", "POST"])
# @main.route("/object-detection/message/manage/<int:id>", methods=["GET", "POST"])
# def manage_message(id=None):
#     return render_template(
#         "manage_message.html", title="Manage Message", current_user=current_user
#     )

# # DONE
# @main.route("/report/detected-object", methods=["GET"])
# def detected_object():
#     page = request.args.get("page", 1, type=int)
#     per_page = 10  # Jumlah objek per halaman
#     search_query = request.args.get("search_query")

#     if search_query:
#         detected_objects = (
#             DetectedObject.query.join(Detector)
#             .join(CCTV)
#             .filter(DetectedObject.name.like(f"%{search_query}%"))
#             .order_by(DetectedObject.timestamp.desc())
#             .paginate(page=page, per_page=per_page)
#         )
#     else:
#         detected_objects = (
#             DetectedObject.query.join(Detector)
#             .join(CCTV)
#             .order_by(DetectedObject.timestamp.desc())
#             .paginate(page=page, per_page=per_page)
#         )

#     return render_template(
#         "detected_object.html",
#         detected_objects=detected_objects,
#         search_query=search_query,
#     )

# # DONE
# @main.route("/report/detected-object/view-object/<int:object_id>", methods=["GET"])
# def view_object(object_id):
#     detected_object = DetectedObject.query.get_or_404(object_id)
#     return render_template("view_object.html", detected_object=detected_object)


# Super user
# @main.route("/su", methods=["GET"])
# @login_required
# def su():
#     return render_template("su.html")


# @main.route("/su/all-cards", methods=["GET"])
# @login_required
# def all_cards():
#     allowed = get_allowed_permission_ids()
#     all_cards = suMenu.query.filter(suMenu.permission_id.in_(allowed)).all()

#     results = [
#         {
#             "title": card.title,
#             "url": card.url,
#             "imageUrl": url_for("main.uploaded_file", filename=card.path),
#             "permission_id": card.permission_id
#         }
#         for card in all_cards
#     ]

#     return jsonify(results)


# @main.route("/su/search", methods=["GET"])
# @login_required
# def search():
#     query = request.args.get("query", "")  # Get the query parameter

#     if query:
#         # Perform a search based on the title
#         search_results = suMenu.query.filter(
#             suMenu.permission_id.in_(get_allowed_permission_ids()),
#             suMenu.title.ilike(f"%{query}%")
#             ).all()
#     else:
#         # If no query, return all results
#         search_results = suMenu.query.filter(suMenu.permission_id.in_(get_allowed_permission_ids())).all()

#     # Return the results in JSON format
#     results = [
#         {
#             "title": result.title,
#             "url": result.url,  # Assuming `url` contains the link for the menu item
#             "imageUrl": url_for(
#                 "main.uploaded_file", filename=result.path
#             ),  # Assuming path is stored for image location
#             "permission_id": result.permission_id
#         }
#         for result in search_results
#     ]

#     return jsonify(results)


# def sanitize_filename(filename):
#     return re.sub(r'[<>:"/\\|?*\t\n]', "_", filename)


UPLOAD_FOLDER = "static/suMenus"


# @main.route("/su/upload", methods=["POST"])
# def su_upload():
#     title = request.form.get("title")
#     file_url = request.form.get("url")
#     file = request.files.get("file")

#     if not title or not file:
#         flash("Title and file are required!", "error")
#         return redirect(url_for("main.su"))

#     # Sanitize the filename
#     filename = sanitize_filename(file.filename)

#     # Construct the upload folder path within `static`
#     upload_folder = os.path.join(UPLOAD_FOLDER, title)

#     # Create the directory if it doesn't exist
#     os.makedirs(upload_folder, exist_ok=True)

#     # Construct the full file path
#     # file_path = os.path.join(upload_folder, filename)
#     file_path = f"{upload_folder}/{filename}"

#     # app\static\suMenus
#     # Save the file
#     file.save(file_path)

#     # Create and save the database record
#     new_entry = suMenu(
#         title=title, url=file_url, file=file.read(), path=f"{title}/{filename}"
#     )
#     db.session.add(new_entry)
#     db.session.commit()

#     flash("File uploaded successfully!", "success")
#     return redirect(url_for("main.su"))


@main.route("/static/suMenus/<path:filename>")
def uploaded_file(filename):
    return send_from_directory("static", filename)


# @main.route("/su/approval", methods=["GET"])
# def su_approval():
#     # Check if the current user has the 'manager' role
#     if current_user.role.lower() != "manager":
#         return redirect(url_for('main.su'))
#     # Query users where approval is None or Null
#     applicants = User.query.filter((User.approved.is_(None))).all()
#     return render_template("su_approval.html", applicants=applicants)


# @main.route("/su/update_approval", methods=["POST", "GET"])
# def su_update_approval():
#     # Get the JSON data from the request
#     data = request.get_json()
#     approved_applicants = data.get("approvedApplicants", [])
#     print(approved_applicants)

#     # Iterate over the approved applicants and update the database
#     for applicant in approved_applicants:
#         if "name" in applicant and "email" in applicant and "role" in applicant:
#             # Query the database for the applicant
#             applicant_record = User.query.filter_by(
#                 name=applicant["name"],
#                 phone_number=applicant["email"],
#                 role=applicant["role"],
#             ).first()

#             if applicant_record:
#                 print(applicant_record)
#                 # Update the record
#                 applicant_record.approved = applicant["approved"]
#                 db.session.commit()
#             else:
#                 # Handle case where applicant is not found, if needed
#                 print(f"Applicant not found: {applicant}")

#     return jsonify(
#         {"status": "success", "message": "Approval data updated successfully"}
#     )


# @main.route("/su/get_updated_table", methods=['GET'])
# @login_required
# def get_updated_table():
#     # Fetch the updated applicant data from the database
#     applicants = User.query.filter_by(approved=None).all()
#     # Render only the table rows and return as a response
#     return render_template("su_table_rows.html", applicants=applicants)


# # grant access
# @main.route("/su/grant_access", methods=["GET", "POST"])
# @main.route("/su/grant_access/<int:user_id>", methods=["GET", "POST"])
# def grant_access(user_id=None):
#     if current_user.role.lower() != "manager":
#         return redirect(url_for('main.su'))

#     users = User.query.filter((User.role.ilike('%manager%') == False) & (User.approved == True)).all()
#     permissions = {permission.id: permission.name for permission in Permission.query.all()}

#     allowed_permission_ids = get_allowed_permission_ids()  # Get current user's permissions
#     allowed_permission_names = [permissions[perm_id] for perm_id in allowed_permission_ids]

#     form = AccessForm()
    
#     user = User.query.get(user_id) if user_id else None
#     print("WOI INI USER KEMANA?")
#     print(user)
        
#     # Pre-populate the form permissions with the clicked user's current permissions
#     if user and request.method == 'GET':
        
#         # form.permissions.data = [(up.permission_id, up.permission.name) for up in UserPermission.query.join(Permission).filter(Permission.id==UserPermission.permission_id, UserPermission.user_id==user_id).all()]

#         user_permission_ids = [up.permission_id for up in UserPermission.query.filter_by(user_id=user_id).all()]
#         form.permissions.data = user_permission_ids  # Pre-check the clicked user's current permissions
#         print("LU NAPA KOSONG KOCAK")
#         print(form.permissions.data)
#         return render_template("grant_access.html", users=users, user=user, permissions=permissions, allowed_permission_names=allowed_permission_names, form=form, user_permission_ids=user_permission_ids)

#     if request.method == "POST" and form.validate_on_submit():
#         user_id = request.form.get('user_id')
#         user = User.query.get(user_id)

#         if user:
#             selected_permissions = request.form.getlist("permissions")  # Get selected permissions IDs
            
#             # Remove existing permissions that are not selected
#             UserPermission.query.filter(UserPermission.user_id == user_id,
#                                         UserPermission.permission_id.notin_(selected_permissions)).delete(synchronize_session=False)
            
#             # Add new permissions
#             for permission_id in selected_permissions:
#                 if not UserPermission.query.filter_by(user_id=user_id, permission_id=permission_id).first():
#                     new_permission = UserPermission(user_id=user_id, permission_id=permission_id)
#                     db.session.add(new_permission)
            
#             db.session.commit()
#             flash('Permissions updated successfully!', 'success')
#         else:
#             flash('User not found!', 'danger')

#         return redirect(url_for('main.grant_access'))

#     return render_template("grant_access.html", users=users, user=user, permissions=permissions, allowed_permission_names=allowed_permission_names, form=form)



@main.route('/set_session', methods=['POST'])
def set_session():
    permission_id = request.form.get('id')    
    if permission_id:
        permission = Permission.query.get(permission_id)
        session['permission_name'] = permission.name
        session['permission_id'] = permission_id
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'No ID provided'}), 400

@main.app_context_processor
def inject_session_permission():
    return dict(session_permission=session.get('permission_id', ''), permission_name=session.get('permission_name', ''))

# buat test
# NOTIFICATION RULE
# @main.route('/object-detection/notification-rule/manage', methods=['GET', 'POST'])
# @main.route('/object-detection/notification-rule/manage/<int:rule_id>', methods=['GET', 'POST'])
# def manage_notification_rules(rule_id=None):
#     if rule_id:
#         message = MessageTemplate.query.get(rule_id)
#         message_form = MessageTemplateForm(obj=message)
#         message_title = "Edit Message"
#     else:
#         message = None
#         message_form = MessageTemplateForm()
#         message_title = "Add New Message"

#     if message_form.validate_on_submit() and 'submit_message' in request.form:
#         if message:
#             message.name = message_form.name.data
#             message.template = message_form.template.data
#         else:
#             new_message = MessageTemplate(
#                 name=message_form.name.data,
#                 template=message_form.template.data,
#                 role=session.get('role')
#             )
#             db.session.add(new_message)
#         db.session.commit()
#         flash('Message updated!' if message else 'Message added!', 'success')
#         return redirect(url_for('main.manage_notification_rules'))

#     # Handling Notification Rule form
#     rule_id = request.form.get('rule_id')
#     if rule_id:
#         rule = NotificationRule.query.get(rule_id) or None
#         rule_form = NotificationRuleForm(obj=rule) 
#         rule_title = "Edit Notification Rule"
#     else:
#         rule = None
#         rule_form = NotificationRuleForm()
#         rule_form.detector_id.choices.insert(0, (0, 'Select Detector'))
#         rule_form.contact_id.choices.insert(0, (0, 'Select Contact'))
#         rule_form.message_template_id.choices.insert(0, (0, 'Select Message Template'))
#         rule_title = "Add New Notification Rule"

#     if rule_form.validate_on_submit() and 'submit_rule' in request.form:
#         if rule:
#             rule.detector_id = rule_form.detector_id.data
#             rule.contact_id = rule_form.contact_id.data
#             rule.message_template_id = rule_form.message_template_id.data
#         else:
#             new_rule = NotificationRule(
#                 detector_id=rule_form.detector_id.data,
#                 contact_id=rule_form.contact_id.data,
#                 message_template_id=rule_form.message_template_id.data,
#                 role=session.get('role')
#             )
#             db.session.add(new_rule)
#         db.session.commit()
#         flash('Rule updated!' if rule else 'Rule added!', 'success')
#         return redirect(url_for('main.manage_notification_rules'))

#     messages = MessageTemplate.query.filter(MessageTemplate.permission_id.in_(get_allowed_permission_ids())).all()
#     rules = NotificationRule.query.filter(NotificationRule.permission_id.in_(get_allowed_permission_ids())).all()
    
#     return render_template(
#         'manage_notification_rules.html', 
#         message_form=message_form, 
#         rule_form=rule_form, 
#         messages=messages, 
#         rules=rules,
#         message_title=message_title,
#         rule_title=rule_title
#     )

