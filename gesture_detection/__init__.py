from utils.detector import BaseDetector
from app.models import DetectedObject
from app.extensions import db
from datetime import datetime
import cv2

from flask import current_app
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import os
import time

class GestureForHelpDetector(BaseDetector):
    def __init__(self):
        super().__init__("weights/yolov8m-gesture.pt", "Gesture")

    def process_results(self, results, frame, camera_id):
        with self.app.app_context():
            objects = ""
            # for c in results[0].boxes.cls:
            #     name = self.model.names[int(c)]
            #     if name == "cross-hands":
            #         objects += f"{name}, - "        
            # print(f"Gesture for Help detected on camera {camera_id}.")
            if 0 in results[0].boxes.cls:

                detected_obj = DetectedObject(
                    detector_id=camera_id,
                    name='cross-hands',
                    frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                    timestamp=datetime.now()
                )
                db.session.add(detected_obj)
                db.session.commit()
                
                target = '"Nomerku"'
                message = f"Subject: *SOS DETECTED*||• Camera ID: {camera_id}||• Violation: cross-hands||• timestamp: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
                
                image_filename = f"unfocused_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                image_path = os.path.join(os.getcwd(), image_filename)
                cv2.imwrite(image_path, frame)
                
                app = current_app._get_current_object()
                contact_path = f'//span[contains(@title, {target})]'
                contact = app.wait.until(EC.presence_of_element_located((By.XPATH, contact_path)))
                contact.click()
                
                attachment_box_path = '//*[@id="main"]/footer/div[1]/div/span[2]/div/div[1]/div[2]/div/div'
                attachment_box = app.wait.until(EC.presence_of_element_located((By.XPATH, attachment_box_path)))
                attachment_box.click()
                
                file_input_path = '//*[@id="main"]/footer/div[1]/div/span[2]/div/div[1]/div[2]/div/span/div/ul/div/div[2]/li/div/input'
                file_input = app.wait.until(EC.presence_of_element_located((By.XPATH, file_input_path)))
                file_input.send_keys(os.path.abspath(image_path))
                
                caption_box_path = '//*[@id="app"]/div/div[2]/div[2]/div[2]/span/div/div/div/div[2]/div/div[1]/div[3]/div/div/div[2]/div[1]/div[1]'
                caption_box = app.wait.until(EC.presence_of_element_located((By.XPATH, caption_box_path)))
                for part in message.split('||'):
                    caption_box.send_keys(part)
                    caption_box.send_keys(Keys.SHIFT + Keys.ENTER)
                caption_box.send_keys(Keys.ENTER)
                
                os.remove(image_path)
        annotated_frame = results[0].plot()
        with self.lock:
            self.frames[camera_id] = annotated_frame
        
        time_interval = 15    
        time.sleep(time_interval)
        
