import threading
import cv2
import numpy as np
from datetime import datetime
from utils.detector import BaseDetector
from app.models import DetectedObject
from app.extensions import db
from flask import current_app
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import os
import time
from utils.wa import send_whatsapp_message
from ultralytics import YOLO

BODY_KEYPOINTS = {
    "nose": 0,
    "left_eye": 1,
    "right_eye": 2,
    "left_ear": 3,
    "right_ear": 4,
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_elbow": 7,
    "right_elbow": 8,
    "left_wrist": 9,
    "right_wrist": 10,
    "left_hip": 11,
    "right_hip": 12,
    "left_knee": 13,
    "right_knee": 14,
    "left_ankle": 15,
    "right_ankle": 16
}

X_POS = 0
Y_POS = 1
CONF = 2

def calculate_angle(a, b, c):
    ab = np.array(a) - np.array(b)
    bc = np.array(c) - np.array(b)
    dot_product = np.dot(ab, bc)
    magnitude_ab = np.linalg.norm(ab)
    magnitude_bc = np.linalg.norm(bc)
    cos_theta = dot_product / (magnitude_ab * magnitude_bc)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    angle = np.arccos(cos_theta)
    angle_degrees = np.degrees(angle)
    return angle_degrees

def is_wrist_facing_up(elbow, wrist, shoulder):
    return wrist[Y_POS] < elbow[Y_POS] and wrist[Y_POS] < shoulder[Y_POS]

def are_wrist_keypoints_close(wrist1, wrist2, threshold=30):
    distance = np.sqrt((wrist1[X_POS] - wrist2[X_POS]) ** 2 + (wrist1[Y_POS] - wrist2[Y_POS]) ** 2)
    return distance < threshold

def are_wrist_keypoints_same(wrist1, wrist2, tolerance=5):
    return abs(wrist1[X_POS] - wrist2[X_POS]) < tolerance and abs(wrist1[Y_POS] - wrist2[Y_POS]) < tolerance

def is_keypoint_confident(keypoint, min_confidence=0.5):
    return keypoint[CONF] >= min_confidence

class GestureForHelpDetector(BaseDetector):
    def __init__(self):
        super().__init__("weights/pose.pt", "Gesture")
        self.pose_model = YOLO('pose.pt')
        self.pose_model.to('cuda')

    def process_results(self, results, frame, camera_id):
        with self.app.app_context():
            objects = ""

            # Run pose detection
            pose_results = self.pose_model(frame)
            annotated_frame = pose_results[0].plot()
            
            for obj_idx in range(len(pose_results[0].keypoints)):
                keypoints = pose_results[0].keypoints[obj_idx].data[0]
                # Ensure keypoints exist and are not empty
                if keypoints is not None and keypoints.size(0) > 0:
                    right_shoulder = keypoints[BODY_KEYPOINTS["right_shoulder"]][:2].tolist()
                    right_elbow = keypoints[BODY_KEYPOINTS["right_elbow"]][:2].tolist()
                    right_wrist = keypoints[BODY_KEYPOINTS["right_wrist"]][:2].tolist()
                    left_shoulder = keypoints[BODY_KEYPOINTS["left_shoulder"]][:2].tolist()
                    left_elbow = keypoints[BODY_KEYPOINTS["left_elbow"]][:2].tolist()
                    left_wrist = keypoints[BODY_KEYPOINTS["left_wrist"]][:2].tolist()
                    nose = keypoints[BODY_KEYPOINTS["nose"]][:2].tolist()
                    
                    right_elbow_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
                    left_elbow_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)

                    right_is_strong = 40 <= right_elbow_angle <= 100 and is_wrist_facing_up(right_elbow, right_wrist, right_shoulder)
                    left_is_strong = 40 <= left_elbow_angle <= 100 and is_wrist_facing_up(left_elbow, left_wrist, left_shoulder)
                    
                    cv2.putText(
                        annotated_frame, 'Right Elbow Angle:',
                        (int(right_elbow[0]), int(right_elbow[1]) - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA
                    )
                    cv2.putText(
                        annotated_frame, f'{right_elbow_angle:.2f} deg',
                        (int(right_elbow[0]), int(right_elbow[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA
                    )
                    cv2.putText(
                        annotated_frame, 'Left Elbow Angle:',
                        (int(left_elbow[0]), int(left_elbow[1]) - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA
                    )
                    cv2.putText(
                        annotated_frame, f'{left_elbow_angle:.2f} deg',
                        (int(left_elbow[0]), int(left_elbow[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA
                    )
                    
                    if right_is_strong and left_is_strong:
                        cv2.putText(
                            annotated_frame, 'STRONG',
                            (int(nose[0]), int(nose[1]) - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA
                        )
                    
                    if (is_keypoint_confident(keypoints[BODY_KEYPOINTS["right_shoulder"]]) and
                        is_keypoint_confident(keypoints[BODY_KEYPOINTS["right_elbow"]]) and
                        is_keypoint_confident(keypoints[BODY_KEYPOINTS["right_wrist"]]) and
                        is_keypoint_confident(keypoints[BODY_KEYPOINTS["left_shoulder"]]) and
                        is_keypoint_confident(keypoints[BODY_KEYPOINTS["left_elbow"]]) and
                        is_keypoint_confident(keypoints[BODY_KEYPOINTS["left_wrist"]])):
                        if are_wrist_keypoints_close(left_wrist, right_wrist) or are_wrist_keypoints_same(left_wrist, right_wrist):
                            cv2.putText(
                                annotated_frame, 'Arms Crossing',
                                (int(nose[0]), int(nose[1]) - 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA
                            )
                            
                            # capture
                            detected_obj = DetectedObject(
                                detector_id=camera_id,
                                name='cross-hands',
                                frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                                timestamp=datetime.now()
                            )
                            db.session.add(detected_obj)
                            db.session.commit()

                            target = "Y0L0"
                            message = f"Subject: *SOS DETECTED*||• Camera ID: {camera_id}||• Violation: cross-hands||• timestamp: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"

                            image_filename = f"unfocused_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            image_path = os.path.join(os.getcwd(), image_filename)
                            cv2.imwrite(image_path, frame)

                            threading.Thread(target=send_whatsapp_message, args=(current_app._get_current_object(), target, message, image_path)).start()
            
            with self.lock:
                self.frames[camera_id] = annotated_frame

            time_interval = 15
            # time.sleep(time_interval)
