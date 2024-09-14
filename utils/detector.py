# import os
# import re
# from telnetlib import EC
# import time
# from colorama import Back, Style
# import cv2
# from flask import current_app, session
# from flask_login import current_user
# from ultralytics import YOLO
# from app.models import CCTV, Camera, Contact, Detector, DetectedObject, DetectorType, MessageTemplate, NotificationRule, Weight
# import threading
# from datetime import datetime
# import time
# import queue
# # from utils.wa import send_whatsapp_message
# from collections import defaultdict


# import threading
# import cv2
# import time

# class CameraStreamManager:
#     def __init__(self):
#         self.camera_streams = {}
#         self.lock = threading.Lock()

#     def get_camera_stream(self, ip_address):
#         with self.lock:
#             if ip_address not in self.camera_streams:
#                 # Start new thread for the camera if not already started
#                 camera_stream = CameraStream(ip_address)
#                 camera_stream.start()
#                 self.camera_streams[ip_address] = camera_stream
#             return self.camera_streams[ip_address]

#     def stop_all(self):
#         with self.lock:
#             for camera_stream in self.camera_streams.values():
#                 camera_stream.stop()
#             self.camera_streams.clear()

# class CameraStream(threading.Thread):
#     def __init__(self, ip_address):
#         super().__init__()
#         self.ip_address = ip_address
#         self.capture = cv2.VideoCapture(ip_address)
#         self.frame = None
#         self.running = True
#         self.lock = threading.Lock()

#     def run(self):
#         while self.running:
#             ret, frame = self.capture.read()
#             if ret:
#                 with self.lock:
#                     self.frame = frame

#     def get_frame(self):
#         with self.lock:
#             return self.frame

#     def stop(self):
#         self.running = False
#         self.capture.release()

# class DetectorThread(threading.Thread):
#     def __init__(self, detector, camera_stream):
#         super().__init__()
#         self.detector = detector
#         self.camera_stream = camera_stream
#         self.running = True

#     def run(self):
#         while self.running:
#             frame = self.camera_stream.get_frame()
#             if frame is not None:
#                 detected_objects = self.detector.process_frame(frame)                    


#     def stop(self):
#         self.running = False

# class DetectorManager:
#     def __init__(self, session):
#         self.session = session
#         self.detectors = {}
#         self.camera_manager = CameraStreamManager()
#         self.lock = threading.Lock()

#     def initialize_detectors(self):
#         with self.lock:
#             active_detectors = get_active_detectors(self.session)
#             for detector in active_detectors:
#                 cctv = self.session.query(CCTV).get(detector.cctv_id)
                
#                 # Get the shared camera stream for this IP address
#                 camera_stream = self.camera_manager.get_camera_stream(cctv.ip_address)

#                 # Start a separate thread for each detector processing the frame
#                 detector_thread = DetectorThread(detector, camera_stream)
#                 detector_thread.start()

#                 self.detectors[detector.id] = detector_thread

#     def update_detectors(self):
#         with self.lock:
#             active_detectors = get_active_detectors(self.session)
#             active_detector_ids = {detector.id for detector in active_detectors}

#             # Stop detectors that are no longer active
#             to_stop = [detector_id for detector_id in self.detectors if detector_id not in active_detector_ids]
#             for detector_id in to_stop:
#                 self.detectors[detector_id].stop()
#                 del self.detectors[detector_id]

#             # Start new detectors
#             for detector in active_detectors:
#                 if detector.id not in self.detectors:
#                     cctv = self.session.query(CCTV).get(detector.cctv_id)
#                     camera_stream = self.camera_manager.get_camera_stream(cctv.ip_address)
#                     detector_thread = DetectorThread(detector, camera_stream)
#                     detector_thread.start()
#                     self.detectors[detector.id] = detector_thread

#     def stop_all(self):
#         with self.lock:
#             for detector_thread in self.detectors.values():
#                 detector_thread.stop()
#             self.detectors.clear()
#             self.camera_manager.stop_all()

# # Query untuk mendapatkan semua detektor yang aktif
# def get_active_detectors(session):
#     return session.query(Detector).filter(Detector.running == True).all()
    