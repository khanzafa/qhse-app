from utils.detector import BaseDetector
from app.models import DetectedObject
from app.extensions import db
from datetime import datetime
import cv2
import threading

from flask import current_app
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import os
import time
from utils.wa import send_whatsapp_message

class PPEDetector(BaseDetector):
    def __init__(self):
        super().__init__("weights/ppe-detection.pt", "PPE")
        
    def process_results(self, results, frame, detector_id):
        with self.app.app_context():
            objects = set()  # Use a set to avoid duplicates
            for c in results[0].boxes.cls:
                name = self.model.names[int(c)]
                if name == "No helmet" or name == "No vest":
                    objects.add(name)  # Add to the set to ensure uniqueness

            if objects:
                # Convert set to comma-separated string
                objects_str = ", - ".join(objects)
                print(f"PPE violation detected on camera {detector_id}.")
                detected_obj = DetectedObject(
                    detector_id=detector_id,
                    name=objects_str,
                    frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                    timestamp=datetime.now()
                )
                db.session.add(detected_obj)
                db.session.commit()
                
                target = '"You "' # Kontak WA sesuai nama
                message = f"Subject: *PPE Violation*||• Camera ID: {detector_id}||• Violation: {objects}||• timestamp: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
                
                image_filename = f"ppe_violation_{detector_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                image_path = os.path.join(os.getcwd(), image_filename)
                cv2.imwrite(image_path, frame)                
                
                # Send the WhatsApp message using the helper function
                # threading.Thread(target=send_whatsapp_message, args=(current_app._get_current_object(), target, message, image_path)).start()

        annotated_frame = results[0].plot()
        with self.lock:
            self.frames[detector_id] = annotated_frame
        
        time_interval = 45
        time.sleep(time_interval)
