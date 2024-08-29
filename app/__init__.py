# app/__init__.py
import threading
from flask import Flask, current_app
from base64 import b64encode
from app.extensions import db, migrate
from ppe_detection import PPEDetector
from gesture_detection import GestureForHelpDetector
from unfocused_detection import UnfocusedDetector
from ppe_detection.routes import ppe
from gesture_detection.routes import gesture
from unfocused_detection.routes import unfocused
from guide_bot.routes import guide_bot
from api.routes import api
from flask_login import LoginManager
from app.models import User

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import os

ppe_detector = PPEDetector()
gesture_detector = GestureForHelpDetector()
unfocused_detector = UnfocusedDetector()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app():
    
    app = Flask(__name__)
    print("App created.")
    app.config.from_object('config.Config')
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # Define the b64encode filter
    def base64_encode(data):
        return b64encode(data).decode('utf-8')

    # Add the filter to the Jinja2 environment
    app.jinja_env.filters['b64encode'] = base64_encode

    db.init_app(app)
    print("Database initialized.")
    migrate.init_app(app, db)
    print("Migration initialized.")
    login_manager.init_app(app)
    print("Login manager initialized.")
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def start_detector(detector):
        with app.app_context():
            detector.run(app)

    from app.routes import main
    from app.auth import auth as auth_blueprint
    app.register_blueprint(main)
    print("Main blueprint registered.")
    app.register_blueprint(ppe)
    print("PPE blueprint registered.")
    app.register_blueprint(gesture)
    print("Gesture blueprint registered.")
    app.register_blueprint(unfocused)
    print("Unfocused blueprint registered.")
    app.register_blueprint(guide_bot)
    print("Guide bot blueprint registered.")
    app.register_blueprint(auth_blueprint)
    print("Auth blueprint registered.")
    # app.register_blueprint(api)
    # print("API blueprint registered.")

    user_home_dir = os.path.expanduser("~")
    user_home_dir = user_home_dir.replace("\\", "/")
    
    # option = webdriver.ChromeOptions()
    # option.add_argument(f'user-data-dir={user_home_dir}/AppData/Local/Google/Chrome/User Data --headless')
    # option.add_experimental_option("detach", True)
    # option.add_experimental_option("excludeSwitches", ["enable-automation"])
    # option.add_experimental_option('useAutomationExtension', False)
    # app.driver = webdriver.Chrome(options=option)
    # app.driver.get("https://web.whatsapp.com/")
    # app.wait = WebDriverWait(app.driver, 100)

    threading.Thread(target=start_detector, args=(ppe_detector,)).start()
    print("PPE detector started.")
    threading.Thread(target=start_detector, args=(gesture_detector,)).start()
    print("Gesture detector started.")
    threading.Thread(target=start_detector, args=(unfocused_detector,)).start()
    print("Unfocused detector started.")

    return app