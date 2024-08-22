from utils.detector import BaseDetector
from app.models import DetectedObject
from app.extensions import db
from datetime import datetime
import cv2

from flask import current_app
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

class PPEDetector(BaseDetector):
    def __init__(self):
        super().__init__("weights/ppe-detection.pt", "PPE")

    def process_results(self, results, frame, detector_id):       
        with self.app.app_context():
            objects = ""
            for c in results[0].boxes.cls:
                name = self.model.names[int(c)]
                if name == "No helmet" or name == "No vest":
                    objects += f"{name}, - "
            print(f"PPE violation detected on detector {detector_id}.")
            detected_obj = DetectedObject(
                detector_id=detector_id,
                name=objects,
                frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                timestamp=datetime.now()
            )
            db.session.add(detected_obj)
            db.session.commit()
            
            
        annotated_frame = results[0].plot()
        with self.lock:
            self.frames[detector_id] = annotated_frame
            print(f"Frame for detector ID {detector_id} updated.")