# ppe_detection/detector.py
import time
import cv2
from ultralytics import YOLO
from app.models import Camera, Detector
import threading

class PPEDetector():
    def __init__(self):
        super().__init__()
        self.model = YOLO("weights/yolov8n.pt")
        self.running = False
        self.frames = {}
        self.lock = threading.Lock()  # Tambahkan lock untuk akses thread-safe ke frames

    def run(self):
        self.running = True
        while self.running:
            # Dapatkan daftar IP dari database
            cctvs = Camera.query.join(Detector).filter(Detector.name == "PPE", Detector.running == True).all()
            threads = []
            for cctv in cctvs:
                t = threading.Thread(target=self.process_video, args=(cctv.ip_address, cctv.id))
                threads.append(t)
                t.start()             
                
            # Wait for all threads to complete
            for t in threads:
                t.join() 
        
    def process_video(self, video_source, camera_id):
        video_source = 0 if video_source == "http://0.0.0.0" else video_source
        
        max_retries = 5
        retry_interval = 5  # Interval waktu dalam detik untuk retry

        for attempt in range(max_retries):
            cap = cv2.VideoCapture(video_source)
            if cap.isOpened():
                print(f"Connected to {video_source} on attempt {attempt + 1}")
                break
            else:
                print(f"Error: Tidak dapat membuka video dari {video_source}. Attempt {attempt + 1}/{max_retries}")
                cap.release()
                time.sleep(retry_interval)
        else:
            print(f"Failed to open video from {video_source} after {max_retries} attempts.")
            return
        
        while self.running and cap.isOpened():
            success, frame = cap.read()
            if success:
                results = self.model(frame, stream=False)
                annotated_frame = results[0].plot()
                with self.lock:
                    self.frames[camera_id] = annotated_frame
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print(f"Error: Lost connection to {video_source}.")
                break
        
        cap.release()

    def stop(self):
        self.running = False