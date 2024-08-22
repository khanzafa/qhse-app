from flask import current_app
from utils.detector import BaseDetector
from app.models import DetectedObject
from app.extensions import db
from datetime import datetime
import cv2

class UnfocusedDetector(BaseDetector):
    def __init__(self):
        super().__init__("weights/best_weight_drowsiness.pt", "Unfocused")

    # def process_results(self, results, frame, camera_id):
    #     if 'unfocused' in [results[0].names[int(cls)] for cls in results[0].boxes.cls]:
    #         print(f"Unfocused object detected on camera {camera_id}.")
    #         detected_obj = DetectedObject(
    #             detector_id=camera_id,
    #             name='unfocused',
    #             frame=cv2.imencode('.jpg', frame)[1].tobytes(),
    #             timestamp=datetime.now()
    #         )
    #         db.session.add(detected_obj)
    #         db.session.commit()
    #     annotated_frame = results[0].plot()
    #     with self.lock:
    #         self.frames[camera_id] = annotated_frame

    def process_results(self, results, frame, camera_id):
        # Ensure that app context is available
        with self.app.app_context():
            objects = ""
            for c in results[0].boxes.cls:
                name = self.model.names[int(c)]
                objects += f"{name}, - "
            detected_obj = DetectedObject(
                detector_id=camera_id,
                name=objects,
                frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                timestamp=datetime.now()
            )
            db.session.add(detected_obj)
            db.session.commit()
            annotated_frame = results[0].plot()
            with self.lock:
                self.frames[camera_id] = annotated_frame
