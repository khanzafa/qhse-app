from utils.detector import BaseDetector
from app.models import DetectedObject
from app.extensions import db
from datetime import datetime
import cv2

class PPEDetector(BaseDetector):
    def __init__(self):
        super().__init__("weights/ppe-detection.pt", "PPE")

    def process_results(self, results, frame, camera_id):
        res = results[0].boxes.cls
        if 0 in results[0].boxes.cls or 1 in results[0].boxes.cls:
            class_names = self.model.names
            name = class_names[0] if 0 in res else class_names[1]
            print(f"PPE violation detected on camera {camera_id}.")
            detected_obj = DetectedObject(
                detector_id=camera_id,
                name=name,
                frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                timestamp=datetime.now()
            )
            db.session.add(detected_obj)
            db.session.commit()
        annotated_frame = results[0].plot()
        with self.lock:
            self.frames[camera_id] = annotated_frame