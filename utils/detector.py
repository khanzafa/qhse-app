import time
import cv2
from ultralytics import YOLO
from app.models import Camera, Detector, DetectedObject
import threading
from datetime import datetime

class BaseDetector:
    def __init__(self, model_path, detector_name):
        self.model = YOLO(model_path) # tambahi .to('cpu')
        self.detector_name = detector_name
        self.running = False
        self.frames = {}
        self.lock = threading.Lock()  # Thread-safe access to frames

    def run(self, app):
        self.running = True
        self.app = app
        while self.running:
            cctvs = Camera.query.join(Detector).filter(Detector.type == self.detector_name, Detector.running == True).all()
            threads = []
            for cctv in cctvs:
                t = threading.Thread(target=self.process_video, args=(cctv.ip_address, cctv.detector.id))
                threads.append(t)
                with app.app_context():
                    t.start()
                
            for t in threads:
                t.join()

    def process_video(self, video_source, detector_id):
        video_source = 0 if video_source == "http://0.0.0.0" else video_source

        max_retries = 5
        retry_interval = 5  # Interval between retries

        for attempt in range(max_retries):
            cap = cv2.VideoCapture(video_source)
            if cap.isOpened():
                print(f"Connected to {video_source} on attempt {attempt + 1}")
                break
            else:
                print(f"Error: Cannot open video from {video_source}. Attempt {attempt + 1}/{max_retries}")
                cap.release()
                time.sleep(retry_interval)
        else:
            print(f"Failed to open video from {video_source} after {max_retries} attempts.")
            return

        while self.running and cap.isOpened():
            success, frame = cap.read()
            if success:
                results = self.model(frame, stream=False)
                self.process_results(results, frame, detector_id)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print(f"Error: Lost connection to {video_source}.")
                break

        cap.release()

    def process_results(self, results, frame, detector_id):
        raise NotImplementedError("This method should be overridden by subclasses")

    def stop(self):
        self.running = False
