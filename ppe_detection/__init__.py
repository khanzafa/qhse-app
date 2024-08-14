from utils.detector import BaseDetector
from app.models import DetectedObject
from app.extensions import db
from datetime import datetime
import cv2

class PPEDetector(BaseDetector):
    def __init__(self):
        super().__init__("weights/ppe-detection.pt", "PPE")

    def process_results(self, results, frame, camera_id):       
        with self.app.app_context():
            objects = ""
            for c in results[0].boxes.cls:
                name = self.model.names[int(c)]
                if name == "No helmet" or name == "No vest":
                    objects += f"{name}, - "
            print(f"PPE violation detected on camera {camera_id}.")
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