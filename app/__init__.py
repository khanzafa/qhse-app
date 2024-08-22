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

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

ppe_detector = PPEDetector()
gesture_detector = GestureForHelpDetector()
unfocused_detector = UnfocusedDetector()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # Define the b64encode filter
    def base64_encode(data):
        return b64encode(data).decode('utf-8')

    # Add the filter to the Jinja2 environment
    app.jinja_env.filters['b64encode'] = base64_encode

    db.init_app(app)
    migrate.init_app(app, db)

    def start_detector(detector):
        with app.app_context():
            detector.run(app)

    from app.routes import main
    app.register_blueprint(main)
    app.register_blueprint(ppe)
    app.register_blueprint(gesture)
    app.register_blueprint(unfocused)
    app.register_blueprint(guide_bot)
    
    threading.Thread(target=start_detector, args=(ppe_detector,)).start()
    threading.Thread(target=start_detector, args=(gesture_detector,)).start()
    # threading.Thread(target=start_detector, args=(unfocused_detector,)).start()

    return app