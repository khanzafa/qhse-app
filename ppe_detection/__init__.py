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
from utils.wa import send_whatsapp_message
from colorama import Fore, Back, Style

class PPEDetector(BaseDetector):
    def __init__(self):
        super().__init__("weights/ppe-detection.pt", "PPE")
        
    def process_results(self, results, frame, camera_id):       
        with self.lock: 
            self.frame_number += 1
            
        with self.app.app_context(): # To know its context
            objects = set()  # Use a set to avoid duplicates
            for c in results[0].boxes:
                track_id = c.id if hasattr(c, 'id') else None
                track_id = int(track_id.item())  # Convert from tensor to int
                class_id = c.cls
                name = self.model.names[int(class_id)]
                print(Back.GREEN + '**************************************************************')
                print(f"Detected {name} with track ID {track_id}, frame_number: {self.frame_number}")
                print(Style.RESET_ALL)
                
                # Before accessing or updating the tracker, print its state
                print(f"Tracker State BEFORE processing frame {self.frame_number}: {self.detected_objects_tracker}")
                
                if name == "No helmet" or name == "No vest":
                    if track_id is not None:
                        with self.lock:
                            print(Back.YELLOW + f"Track ID: {track_id}")
                            print(f"Initial count: {self.detected_objects_tracker[track_id]['count']}, Last frame: {self.detected_objects_tracker[track_id]['last_frame']}")
                            print(Style.RESET_ALL)
                            
                            # If first time detection or reset count due to detection gap
                            if self.detected_objects_tracker[track_id]["count"] == 0:
                                print(Back.GREEN + "First detection or reset after gap")
                                objects.add(name)  # First detection, send message
                                self.detected_objects_tracker[track_id]["count"] += 1
                                print(f"Object added: {name}, Count updated to: {self.detected_objects_tracker[track_id]['count']}")
                                
                            # Detected again in consecutive frames
                            elif self.detected_objects_tracker[track_id]["last_frame"] == self.frame_number - 1:
                                print(Back.CYAN + "Detected in consecutive frames")
                                self.detected_objects_tracker[track_id]["count"] += 1
                                print(f"Count updated to: {self.detected_objects_tracker[track_id]['count']}")
                                
                            else:
                                # Reset count if there's a gap in detection
                                print(Back.MAGENTA + "Detection gap detected, resetting count")
                                self.detected_objects_tracker[track_id]["count"] = 1
                                print(f"Count reset to: {self.detected_objects_tracker[track_id]['count']}")

                            # Check if the object has been detected for 5 consecutive frames
                            if self.detected_objects_tracker[track_id]["count"] >= 5:
                                print(Back.RED + "Detected for 5 consecutive frames, adding to objects and sending message")
                                objects.add(name)  # Send WhatsApp message
                                self.detected_objects_tracker[track_id]["count"] = 0  # Reset the count after sending the message
                                print(f"Message sent. Count reset to: {self.detected_objects_tracker[track_id]['count']}")

                            # Update last_frame at the end, regardless of the branch
                            self.detected_objects_tracker[track_id]["last_frame"] = self.frame_number
                            print(Back.BLUE + f"Updated last_frame to current frame: {self.detected_objects_tracker[track_id]['last_frame']}")
                            print(Style.RESET_ALL)


                
            if objects:
                # Convert set to comma-separated string
                objects_str = ", - ".join(objects)
                print(f"PPE violation detected on camera {camera_id}.")
                detected_obj = DetectedObject(
                    detector_id=camera_id,
                    name=objects_str,
                    frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                    timestamp=datetime.now()
                )
                db.session.add(detected_obj)
                db.session.commit()
                
                target = 'eh' # Kontak WA sesuai nama
                message = f"Subject: *PPE Violation*||• Camera ID: {camera_id}||• Violation: {objects}||• timestamp: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} ||• Frame: {self.frame_number}"
                
                image_filename = f"ppe_violation_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                image_path = os.path.join(os.getcwd(), image_filename)
                cv2.imwrite(image_path, frame)
                
                # Add the message to the shared queue
                self.add_message_to_queue(current_app._get_current_object(), target, message, image_path)

        annotated_frame = results[0].plot()
        with self.lock:
            self.frames[camera_id] = annotated_frame
        
        # time_interval = 45
        # time.sleep(time_interval)
