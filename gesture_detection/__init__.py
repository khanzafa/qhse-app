from utils.detector import BaseDetector
from app.models import DetectedObject
from app.extensions import db
from datetime import datetime
import cv2

class GestureForHelpDetector(BaseDetector):
    def __init__(self):
        super().__init__("weights/yolov8n.pt", "Gesture for Help")

    def process_results(self, results, frame, camera_id):
        if 'cross-hands' in [results[0].names[int(cls)] for cls in results[0].boxes.cls]:
            print(f"Gesture for Help detected on camera {camera_id}.")
            detected_obj = DetectedObject(
                detector_id=camera_id,
                name='cross-hands',
                frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                timestamp=datetime.now()
            )
            db.session.add(detected_obj)
            db.session.commit()
        annotated_frame = results[0].plot()
        with self.lock:
            self.frames[camera_id] = annotated_frame
