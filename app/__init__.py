# app/__init__.py
# import threading
import signal
from flask_cors import CORS
from flask_socketio import SocketIO
import threading
from flask import Flask, current_app, request, session
from base64 import b64encode
from app.extensions import db, migrate, swagger
# from guide_bot.routes import guide_bot
from api.routes import api_routes
from app.routes import app_routes
from flask_login import LoginManager
from app.models import User
from app.routes import main
# from aios.routes import aios
from flask_mail import Mail

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import os

from utils.detector import DetectorManager
from utils.message import selenium_manager, mail_manager

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
# Initialize Flask-Mail
mail = Mail()

# Initialize Flask-SocketIO
socketio = SocketIO()

# Misal: Manajer detektor yang telah kita buat sebelumnya
detector_manager = DetectorManager(session)
detector_thread = None  # Global variable to store the detector thread

def run_detectors(app):
    detector_manager.initialize_detectors(app)

# Tangkap sinyal untuk menghentikan detektor saat server dimatikan
def handle_shutdown_signal(signal, frame):
    global detector_thread  # Use the global variable
    
    print("Shutting down detector manager...")
    detector_manager.stop_all()
    print("Detector manager stopped.")
    if detector_thread is not None:
        print("Waiting for detector thread to join...")
        detector_thread.join()  # Ensure the thread is properly joined
        detector_thread = None
        print("Detector thread joined.")

    print("Shutting down server...")
    os._exit(0)  # Force exit the program

def create_app():
    global detector_thread  # Use the global variable 

    app = Flask(__name__)
    print("App created.")
    app.config.from_object('config.Config')
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    # Konfigurasi direktori upload
    UPLOAD_FOLDER = 'uploads'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    app.secret_key='haho'    

    # Membuat direktori upload jika belum ada
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        
    # Define the b64encode filter
    def base64_encode(data):
        return b64encode(data).decode('utf-8')

    # Add the filter to the Jinja2 environment
    app.jinja_env.filters['b64encode'] = base64_encode

    db.init_app(app)
    print("Database initialized.")

    migrate.init_app(app, db)
    print("Migration initialized.")

    swagger.init_app(app)
    print("Swagger initialized.")

    login_manager.init_app(app)
    print("Login manager initialized.")

    # Initialize Flask-SocketIO with the app instance
    socketio.init_app(app)
    print("SocketIO initialized.")
    
    # Initialize Flask-Mail with the app instance
    mail.init_app(app)
    print("Mail initialized.")

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth import auth as auth_blueprint
    app.register_blueprint(main)
    print("Main blueprint registered.")
    app.register_blueprint(auth_blueprint)
    print("Auth blueprint registered.")
    # ganti sesuai kebutuhan
    for route in app_routes:
        app.register_blueprint(route)
    CORS(app, supports_credentials=True)  # Izinkan credentials (cookies) di-cross domain

    mail_manager.init_app(app)
    # Selenium
    # selenium_manager.initialize_driver()    

    # Jalankan thread detektor sebelum memulai Flask
    detector_thread = threading.Thread(target=run_detectors, args=(app,), name="DetectorThread")
    detector_thread.start()

    # Tangkap sinyal SIGINT (Ctrl+C) dan SIGTERM untuk menghentikan detektor saat server dihentikan
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    return app