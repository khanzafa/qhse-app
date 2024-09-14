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
    url_for,
    Response,
    stream_with_context,
    abort,
    jsonify,
)
from app.extensions import db
from app.models import (
    Camera,
    Contact,
    DetectedObject,
    Detector,
    DetectorType,
    User,
    Weight,
    suMenu,
)
from app.forms import (
    AddCCTVForm,
    EditCCTVForm,
    ModelForm,
    SelectCCTVForm,
    ContactForm,
    DetectorForm,
    LoginForm,
    RegistrationForm,
)
from app import gesture_detector, ppe_detector, unfocused_detector
from flask_login import current_user, login_user, logout_user, login_required

main = Blueprint("main", __name__)
# current_user = {'name': 'John'}
GRAPHICS_DIR = "app/static/graphics"


@main.route("/")
def index():
    return render_template("index.html", title="Home", current_user=current_user)


@main.route("/report/dashboard")
@login_required
def dashboard():
    # Fetching data
    num_cctv = Camera.query.count()
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

    return render_template(
        "dashboard.html",
        num_cctv=num_cctv,
        num_detectors=num_detectors,
        num_no_ppe=num_no_ppe,
        num_reckless=num_reckless,
        num_gesture_help=num_gesture_help,
        chatbot_requests=chatbot_requests,
        safety_incidents=safety_incidents,
    )


@main.route("/cctv/view_feed/<int:camera_id>")
def view_cctv_feed(camera_id):
    return render_template(
        "view_cctv_feed.html",
        title="Live CCTV Feed",
        camera_id=camera_id,
        current_user=current_user,
    )


@main.route("/cctv/stream/<int:camera_id>")
def cctv_stream(camera_id):
    camera = Camera.query.get_or_404(camera_id)

    def generate_frames():
        address = 0 if camera.ip_address == "http://0.0.0.0" else camera.ip_address
        cap = cv2.VideoCapture(address)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@main.route("/detector/view_feed/<int:detector_id>")
def view_detector_feed(detector_id):
    return render_template(
        "view_detector_feed.html",
        title="Live Detector Feed",
        detector_id=detector_id,
        current_user=current_user,
    )


@main.route("/detector/stream/<int:detector_id>")
def detector_stream(detector_id):
    detector = Detector.query.get_or_404(detector_id)
    detector_type = detector_type
    detector_types = {
        "PPE": ppe_detector,
        "Gesture": gesture_detector,
        "Unfocused": unfocused_detector,
    }
    detector = detector_types[detector_type]

    def generate_frames():
        while True:
            if detector_id in detector.frames:
                print(
                    f"Detector {detector_id} dengan tipe {detector_type} terdapat frame"
                )
                frame = detector.frames[detector_id]
                print("Frame:", frame)
                # cv2.imshow("Frame", frame)
                ret, buffer = cv2.imencode(".jpg", frame)
                frame = buffer.tobytes()
                yield (
                    b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            else:
                print(
                    f"Detector {detector_id} dengan tipe {detector_type} TIDAK terdapat frame"
                )
                continue

    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@main.route("/cctv/all", methods=["GET"])
def view_all_cctv():
    cameras = Camera.query.all()
    return jsonify([camera.to_dict() for camera in cameras])


@main.route("/cctv/manage", methods=["GET", "POST"])
def manage_cctv():
    form = AddCCTVForm()
    if form.validate_on_submit():
        camera = Camera(
            location=form.location.data, ip_address=form.ip_address.data, status=0
        )
        db.session.add(camera)
        db.session.commit()
        flash("CCTV added successfully!")
        return redirect(url_for("main.manage_cctv"))
    cameras = Camera.query.all()
    return render_template(
        "manage_cctv.html",
        title="Manage CCTV",
        current_user=current_user,
        form=form,
        cameras=cameras,
    )


@main.route("/cctv/edit/<int:id>", methods=["GET", "POST"])
def edit_cctv(id):
    camera = Camera.query.get_or_404(id)
    form = EditCCTVForm(obj=camera)
    if form.validate_on_submit():
        camera.location = form.location.data
        camera.type = form.type.data
        camera.ip_address = form.ip_address.data
        camera.status = form.status.data
        db.session.commit()
        flash("CCTV updated successfully!")
        return redirect(url_for("main.manage_cctv"))
    return render_template(
        "edit_cctv.html", title="Edit CCTV", form=form, current_user=current_user
    )


@main.route("/cctv/delete/<int:id>", methods=["POST"])
def delete_cctv(id):
    camera = Camera.query.get_or_404(id)
    db.session.delete(camera)
    db.session.commit()
    flash("CCTV deleted successfully!", "success")
    return redirect(url_for("main.manage_cctv"))


@main.route("/get_weights/<int:detector_type_id>")
def get_weights(detector_type_id):
    weights = Weight.query.filter_by(detector_type_id=detector_type_id).all()
    weight_list = [{"id": weight.id, "name": weight.name} for weight in weights]
    return jsonify(weight_list)


@main.route("/object-detection/detector/manage", methods=["GET", "POST"])
@main.route("/object-detection/detector/manage/<int:id>", methods=["GET", "POST"])
def manage_detector(id=None):
    if id:
        cctvs = requests.get(f'http://localhost:5000/cctv/{id}')
    else:
        detector = None
        form = DetectorForm()
        title = "Add New Detector"

    cameras = Camera.query.all()
    detector_types = DetectorType.query.all()
    if len(detector_types) == 0:
        detector_types = [
            DetectorType(name="PPE", description="Personal Protective Equipment"),
            DetectorType(name="Gesture", description="Gesture for Help"),
            DetectorType(name="Unfocused", description="Unfocused"),
        ]
        db.session.add_all(detector_types)
        db.session.commit()

    weights = Weight.query.all()
    form.weights.choices = [(weight.id, weight.name) for weight in weights]
    form.camera_id.choices = [(camera.id, camera.location) for camera in cameras]
    form.types.choices = [
        (detector_type.id, detector_type.name) for detector_type in detector_types
    ]

    if form.validate_on_submit():
        if detector:
            detector.camera_id = form.camera_id.data
            detector_type = form.types.data
            detector.running = form.running.data
        else:
            new_detector = Detector(
                camera_id=form.camera_id.data,
                type=form.type.data,
                running=form.running.data,
            )
            db.session.add(new_detector)

        db.session.commit()
        flash(
            "Detector entry updated successfully!"
            if detector
            else "Detector entry added successfully!"
        )
        return redirect(url_for("main.manage_detector"))

    detectors = Detector.query.all()
    return render_template(
        "manage_detector.html",
        form=form,
        detectors=detectors,
        detector=detector,
        title=title,
    )


@main.route("/object-detection/detector/delete/<int:id>")
def delete_detector(id):
    detector = Detector.query.get_or_404(id)
    db.session.delete(detector)
    db.session.commit()
    flash("Detector entry deleted successfully!")
    return redirect(url_for("main.manage_detector"))


@main.route("/object-detection/contact/manage", methods=["GET", "POST"])
@main.route("/object-detection/contact/manage/<int:id>", methods=["GET", "POST"])
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
                phone_number=form.phone_number.data, name=form.name.data
            )
            db.session.add(new_contact)

        db.session.commit()
        flash(
            "Contact entry updated successfully!"
            if contact
            else "Contact entry added successfully!"
        )
        return redirect(url_for("main.manage_contact"))

    whas = Contact.query.all()
    return render_template(
        "manage_contact.html", form=form, whas=whas, contact=contact, title=title
    )


@main.route("/object-detection/contact/delete/<int:id>")
def delete_contact(id):
    contact = Contact.query.get_or_404(id)
    db.session.delete(contact)
    db.session.commit()
    flash("Contact entry deleted successfully!")
    return redirect(url_for("main.manage_contact"))


# Manage model
@main.route("/object-detection/model/manage", methods=["GET", "POST"])
@main.route("/object-detection/model/manage/<int:id>", methods=["GET", "POST"])
def manage_model(id=None):
    if id:
        model = Weight.query.get_or_404(id)
        form = ModelForm(obj=model)
        title = "Edit Model"
    else:
        model = None
        form = ModelForm()
        title = "Add New Model"

    detector_types = DetectorType.query.all()
    form.detector_type.choices = [
        (detector_type.id, detector_type.name) for detector_type in detector_types
    ]

    weights_dir = "weights"
    if form.validate_on_submit():
        print("Model:", model)
        if model:
            model.name = form.name.data
        else:
            form.file.data.save(os.path.join(weights_dir, form.file.data.filename))
            new_model = Weight(
                name=form.name.data,
                detector_type_id=form.detector_type.data,
                file=form.file.data.read(),
                path=os.path.join(weights_dir, form.file.data.filename),
                created_at=datetime.now(),
            )
            db.session.add(new_model)

        db.session.commit()
        flash(
            "Model entry updated successfully!"
            if model
            else "Model entry added successfully!"
        )
        return redirect(url_for("main.manage_model"))

    models = Weight.query.all()
    return render_template(
        "manage_model.html", form=form, models=models, model=model, title=title
    )


@main.route("/object-detection/model/delete/<int:id>", methods=["POST"])
def delete_model(id):
    model = Weight.query.get_or_404(id)
    db.session.delete(model)
    db.session.commit()
    flash("Model deleted successfully!")
    return redirect(url_for("main.manage_model"))


# Manage message
@main.route("/object-detection/message/manage", methods=["GET", "POST"])
@main.route("/object-detection/message/manage/<int:id>", methods=["GET", "POST"])
def manage_message(id=None):
    return render_template(
        "manage_message.html", title="Manage Message", current_user=current_user
    )


@main.route("/report/detected-object", methods=["GET"])
def detected_object():
    page = request.args.get("page", 1, type=int)
    per_page = 10  # Jumlah objek per halaman
    search_query = request.args.get("search_query")

    if search_query:
        detected_objects = (
            DetectedObject.query.join(Detector)
            .join(Camera)
            .filter(DetectedObject.name.like(f"%{search_query}%"))
            .order_by(DetectedObject.timestamp.desc())
            .paginate(page=page, per_page=per_page)
        )
    else:
        detected_objects = (
            DetectedObject.query.join(Detector)
            .join(Camera)
            .order_by(DetectedObject.timestamp.desc())
            .paginate(page=page, per_page=per_page)
        )

    return render_template(
        "detected_object.html",
        detected_objects=detected_objects,
        search_query=search_query,
    )


@main.route("/report/detected-object/view-object/<int:object_id>", methods=["GET"])
def view_object(object_id):
    detected_object = DetectedObject.query.get_or_404(object_id)
    return render_template("view_object.html", detected_object=detected_object)


# Super user
@main.route("/su", methods=["GET", "POST"])
@login_required
def su():
    # Check if the current user has the 'manager' role
    if current_user.role != "manager":
        abort(403)  # Forbidden access
    return render_template("su.html")


@main.route("/su/all-cards", methods=["GET"])
@login_required
def all_cards():
    all_cards = suMenu.query.all()

    results = [
        {
            "title": card.title,
            "url": card.url,
            "imageUrl": url_for("main.uploaded_file", filename=card.path),
        }
        for card in all_cards
    ]

    return jsonify(results)


@main.route("/su/search", methods=["GET"])
@login_required
def search():
    query = request.args.get("query", "")  # Get the query parameter

    if query:
        # Perform a search based on the title
        search_results = suMenu.query.filter(suMenu.title.ilike(f"%{query}%")).all()
    else:
        # If no query, return all results
        search_results = suMenu.query.all()

    # Return the results in JSON format
    results = [
        {
            "title": result.title,
            "url": result.url,  # Assuming `url` contains the link for the menu item
            "imageUrl": url_for(
                "main.uploaded_file", filename=result.path
            ),  # Assuming path is stored for image location
        }
        for result in search_results
    ]

    return jsonify(results)


def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*\t\n]', "_", filename)


UPLOAD_FOLDER = "static/suMenus"


@main.route("/su/upload", methods=["POST"])
def su_upload():
    title = request.form.get("title")
    file_url = request.form.get("url")
    file = request.files.get("file")

    if not title or not file:
        flash("Title and file are required!", "error")
        return redirect(url_for("main.su"))

    # Sanitize the filename
    filename = sanitize_filename(file.filename)

    # Construct the upload folder path within `static`
    upload_folder = os.path.join(UPLOAD_FOLDER, title)

    # Create the directory if it doesn't exist
    os.makedirs(upload_folder, exist_ok=True)

    # Construct the full file path
    # file_path = os.path.join(upload_folder, filename)
    file_path = f"{upload_folder}/{filename}"

    # app\static\suMenus
    # Save the file
    file.save(file_path)

    # Create and save the database record
    new_entry = suMenu(
        title=title, url=file_url, file=file.read(), path=f"{title}/{filename}"
    )
    db.session.add(new_entry)
    db.session.commit()

    flash("File uploaded successfully!", "success")
    return redirect(url_for("main.su"))


@main.route("/static/suMenus/<path:filename>")
def uploaded_file(filename):
    return send_from_directory("static", filename)


@main.route("/su/approval", methods=["GET"])
def su_approval():
    # Query users where approval is None or Null
    applicants = User.query.filter((User.approved.is_(None))).all()
    return render_template("su_approval.html", applicants=applicants)


@main.route("/su/update_approval", methods=["POST", "GET"])
def su_update_approval():
    # Get the JSON data from the request
    data = request.get_json()
    approved_applicants = data.get("approvedApplicants", [])
    print(approved_applicants)

    # Iterate over the approved applicants and update the database
    for applicant in approved_applicants:
        if "name" in applicant and "email" in applicant and "role" in applicant:
            # Query the database for the applicant
            applicant_record = User.query.filter_by(
                name=applicant["name"],
                phone_number=applicant["email"],
                role=applicant["role"],
            ).first()

            if applicant_record:
                print(applicant_record)
                # Update the record
                applicant_record.approved = applicant["approved"]
                db.session.commit()
            else:
                # Handle case where applicant is not found, if needed
                print(f"Applicant not found: {applicant}")

    return jsonify(
        {"status": "success", "message": "Approval data updated successfully"}
    )


@main.route("/su/get_updated_table", methods=['GET'])
@login_required
def get_updated_table():
    # Fetch the updated applicant data from the database
    applicants = User.query.filter_by(approved=None).all()
    # Render only the table rows and return as a response
    return render_template("su_table_rows.html", applicants=applicants)


# test ajax
# @main.route('/dum', methods=['POST'])
# def dum():
#     return 'hah?'
