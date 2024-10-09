from collections import defaultdict
from datetime import datetime
import logging
import threading
import time
from colorama import Back, Style
import cv2
import enum
from flask import jsonify
from ultralytics import YOLO
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import event, Enum
from sqlalchemy.orm import Session
from flask_socketio import emit

class Guest(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), index=True, unique=True)
    otp = db.Column(db.String(256))
    otp_expiry = db.Column(db.DateTime)  # Expiry time for the OTP
    
    def get_id(self):
        return str(self.id)  # Implement this method to return a unique identifier for the guest

    @property
    def is_active(self):
        # Assuming all guests are considered active
        return True
    
    @property
    def is_authenticated(self):
        # Assuming all guests are considered active
        return True
    
    def __repr__(self):
        return f'<Guest {self.id}>'
    
class UserRole(enum.Enum):
    user = 'user'
    admin = 'admin'
    guest = 'guest'

class User(db.Model, UserMixin):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(64), index=True, unique=True)
    phone_number = db.Column(db.String(20), index=True, unique=True)
    role = db.Column(db.Enum(UserRole), default=UserRole.user)
    approved = db.Column(db.Boolean(), default=None)
    otp_code = db.Column(db.String(6), nullable=True)
    otp_expiration = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self): 
        return self.role == UserRole.admin

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone_number': self.phone_number,
            'role': self.role,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f'<User {self.name}>'
    
    def get_id(self):
        return str(self.id)

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    description = db.Column(db.String(120))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }
    
    def __repr__(self):
        return f'<Permission {self.name}>'

class UserPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'))
    user = db.relationship('User', backref=db.backref('user_permissions', lazy=True))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    permission = db.relationship('Permission', backref=db.backref('user_permissions', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'permission_id': self.permission_id
        }
    
    def __repr__(self):
        return f'<UserPermission {self.id}>'
    
class CCTVLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True, unique=True)
    description = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self):
        return f'<CCTVLocation {self.name}>'
        
class CCTV(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cctv_location = db.relationship('CCTVLocation', backref=db.backref('cctvs', lazy=True))
    cctv_location_id = db.Column(db.Integer, db.ForeignKey('cctv_location.id', ondelete='CASCADE', onupdate='CASCADE'))
    type = db.Column(db.String(120), index=True)
    ip_address = db.Column(db.String(120))
    status = db.Column(db.Boolean, default=False)
    permission = db.relationship('Permission', backref=db.backref('cctvs', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'location': self.location,
            'type': self.type,
            'ip_address': self.ip_address,
            'status': self.status,
            'permission_id': self.permission_id
        }
    
    def __repr__(self):
        return f'<CCTV {self.location}>'
    
    def stop(self):
        self.status = False
        db.session.commit()
        print(f"CCTV {self.id} stopped.")

class Weight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    file = db.Column(db.LargeBinary)    
    path = db.Column(db.String(120), index=True)
    detector_type = db.relationship('DetectorType', backref=db.backref('weights', lazy=True))
    detector_type_id = db.Column(db.Integer, db.ForeignKey('detector_type.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_at = db.Column(db.DateTime, index=True)
    permission = db.relationship('Permission', backref=db.backref('weights', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class Detector(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cctv_id = db.Column(db.Integer, db.ForeignKey('cctv.id', ondelete='CASCADE', onupdate='CASCADE'))
    cctv = db.relationship('CCTV', backref=db.backref('detectors', uselist=False, lazy=True))
    detector_type = db.relationship('DetectorType', backref=db.backref('detectors', uselist=False))
    detector_type_id = db.Column(db.Integer, db.ForeignKey('detector_type.id', ondelete='CASCADE', onupdate='CASCADE'))
    weight = db.relationship('Weight', backref=db.backref('detectors', uselist=False))
    weight_id = db.Column(db.Integer, db.ForeignKey('weight.id', ondelete='CASCADE', onupdate='CASCADE'))
    running = db.Column(db.Boolean, default=False)
    permission = db.relationship('Permission', backref=db.backref('detectors', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def to_dict(self):
        return {
            'id': self.id,
            'cctv_id': self.cctv_id,
            'detector_type_id': self.detector_type_id,
            'running': self.running,
            'permission_id': self.permission_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self):
        return f'<Detector {self.id}>'
    
    def stop(self):
        self.running = False
        db.session.commit()
        print(f"Detector {self.id} stopped.")
    
    def process_frame(self, frame, detected_objects_tracker):
        # detected_objects_tracker = defaultdict(lambda: {"count": 0, "last_time": 0})
        frame_number = 0
        
        detector = db.session.query(Detector).filter(Detector.id == self.id).first()
        cctv = db.session.query(CCTV).join(Detector).filter(Detector.id == self.id).first()
        
        if self.weight.detector_type.name == 'Help Gesture':
            from gesture_detection.gesture import Gesture
            annotated_frame, gesture_name = Gesture(frame=frame).process_results()
            print(Back.GREEN)
            print(gesture_name)
            print(Style.RESET_ALL)
            detected_object = DetectedObject(
                    detector_id=self.id,
                    name=gesture_name,
                    frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                    timestamp=datetime.now(),
                    permission_id=self.permission_id                
                )
            
            detected_object_info = {
                    # cctv
                    'cctv_id': cctv.id,
                    'cctv_location': cctv.cctv_location,
                    'cctv_type': cctv.type,
                    'ip_address': cctv.ip_address,
                    'cctv_status': cctv.status,
                    'cctv_permission_id': cctv.permission_id,
                    'cctv_created_at': cctv.created_at,
                    'cctv_updated_at': cctv.updated_at,
                    
                    # detector
                    'detector_id': detector.id,
                    'detector_type_id': detector.detector_type_id,
                    'weight_id': detector.weight_id,
                    'running': detector.running,
                    'detector_permission_id': detector.permission_id,
                    'detector_created_at': detector.created_at,
                    'detector_updated_at': detector.updated_at,
                    
                    'name': gesture_name,
                    'timestamp': datetime.now(),
                }
        else:
            model = YOLO(self.weight.path)
            results = model.track(frame, stream=False, persist=True)
            annotated_frame = results[0].plot()
            detected_objects = []
            current_time = time.time()
            
            current_ids = [int(c.id.item()) for c in results[0].boxes if hasattr(c, 'id') and c.id is not None]
            # Check for each track_id in detected_objects_tracker if it still exists in results[0].boxes
            for track_id in list(detected_objects_tracker.keys()):
                if track_id not in current_ids:
                    # Handle track_id that no longer exists
                    print(f"Track ID {track_id} no longer exists in the current detection.")
                    detected_objects_tracker[track_id]["count"] = 0
                    detected_objects_tracker[track_id]["last_time"] = current_time
            
            for c in results[0].boxes:
                track_id = c.id if hasattr(c, 'id') else None
                track_id = int(track_id.item())
                class_id = c.cls
                name = model.names[int(class_id)]
                
                detected_object_info = {
                    # cctv
                    'cctv_id': cctv.id,
                    'cctv_location': cctv.location,
                    'cctv_type': cctv.type,
                    'ip_address': cctv.ip_address,
                    'cctv_status': cctv.status,
                    'cctv_permission_id': cctv.permission_id,
                    'cctv_created_at': cctv.created_at,
                    'cctv_updated_at': cctv.updated_at,
                    
                    # detector
                    'detector_id': detector.id,
                    'detector_type_id': detector.detector_type_id,
                    'weight_id': detector.weight_id,
                    'running': detector.running,
                    'detector_permission_id': detector.permission_id,
                    'detector_created_at': detector.created_at,
                    'detector_updated_at': detector.updated_at,
                    
                    'name': name,
                    'timestamp': datetime.now(),
                    'track_id': track_id,                    

                }
                
                
                # Object tracking logic
                if track_id is not None:
                    tracker = detected_objects_tracker.get(track_id, {"count": 0, "last_time": current_time})
                    print(Back.RED)
                    print(f"Track id: {track_id}, count: {tracker['count']}, current time: {current_time}")
                    print(f"Current time - last time: {current_time - tracker['last_time']}")
                    print(Style.RESET_ALL)
                    
                    # If Fire
                    if name.lower() == 'fire':
                        # Time gap logic
                        if tracker['count'] == 0:
                            detected_objects.append(detected_object_info)
                            tracker['count'] = 1
                            
                            detected_object = DetectedObject(
                                detector_id=self.id,
                                name=name,
                                frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                                timestamp=datetime.now(),
                                permission_id=self.permission_id                
                            )
                            
                            db.session.add(detected_object)
                        if current_time - tracker['last_time'] >= 3600:
                            detected_objects.append(detected_object_info)
                            tracker['last_time'] = current_time
                            print(Back.YELLOW)
                            print(f"Detected After {current_time - tracker['last_time']} seconds")
                            print(Style.RESET_ALL)
                    else:

                        # Frame gap logic
                        # # First detection or reset due to time gap
                        # if tracker["count"] == 0:
                        #     detected_objects.append(detected_object_info)
                        #     detected_object = DetectedObject(
                        #         detector_id=self.id,
                        #         name=name,
                        #         frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                        #         timestamp=datetime.now(),
                        #         permission_id=self.permission_id                
                        #     )
                            
                        #     db.session.add(detected_object)
                        #     tracker["count"] = 1  # Reset count if a time gap occurs
                        # else:
                        #     tracker["count"] += 1
                        # # Detect object consistently over 30 frames
                        # if tracker["count"] >= 30:
                        #     detected_objects.append(detected_object_info)
                        #     tracker["count"] = 0  # Reset after detection
                            
                            
                        # Time gap logic
                        if tracker['count'] == 0:
                            detected_objects.append(detected_object_info)
                            tracker['count'] = 1
                            
                            detected_object = DetectedObject(
                                detector_id=self.id,
                                name=name,
                                frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                                timestamp=datetime.now(),
                                permission_id=self.permission_id                
                            )
                            
                            db.session.add(detected_object)
                        if current_time - tracker['last_time'] >= 30:
                            detected_objects.append(detected_object_info)
                            tracker['last_time'] = current_time
                            print(Back.YELLOW)
                            print(f"Detected After 3 seconds")
                            print(Style.RESET_ALL)

                        # Update tracker info
                    detected_objects_tracker[track_id] = tracker
                
            db.session.commit()
            
        return detected_objects, annotated_frame, detected_objects_tracker

class DetectorType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True, unique=True)
    description = db.Column(db.String(120))    
    # permission = db.relationship('Permission', backref=db.backref('detectors', uselist=False))
    # permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            # 'permission_id': self.permission_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f'<DetectorType {self.name}>'

class DetectedObject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    detector = db.relationship('Detector', backref=db.backref('detected_objects', lazy=True))
    detector_id = db.Column(db.Integer, db.ForeignKey('detector.id', ondelete='CASCADE', onupdate='CASCADE'))
    name = db.Column(db.String(120), index=True)
    frame = db.Column(db.LargeBinary)
    timestamp = db.Column(db.DateTime, index=True)
    permission = db.relationship('Permission', backref=db.backref('detected_objects', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'detector_id': self.detector_id,
            'name': self.name,
            'frame': self.frame,
            'timestamp': self.timestamp,
            'permission_id': self.permission_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f'<DetectedObject {self.id}>'    
    
class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True, unique=True)
    template = db.Column(db.String(480))
    permission = db.relationship('Permission', backref=db.backref('message_templates', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'template': self.template,
            'permission_id': self.permission_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f'<MessageTemplate {self.name}>'

class NotificationRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    detector_id = db.Column(db.Integer, db.ForeignKey('detector.id', ondelete='CASCADE', onupdate='CASCADE'))
    detector = db.relationship('Detector', backref=db.backref('notification_rules', lazy=True))
    message_template_id = db.Column(db.Integer, db.ForeignKey('message_template.id', ondelete='CASCADE', onupdate='CASCADE'))
    message_template = db.relationship('MessageTemplate', backref=db.backref('notification_rules', lazy=True))
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id', ondelete='CASCADE', onupdate='CASCADE'))
    contact = db.relationship('Contact', backref=db.backref('notification_rules', lazy=True))
    permission = db.relationship('Permission', backref=db.backref('notification_rules', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'detector_id': self.detector_id,
            'message_template_id': self.message_template_id,
            'contact_id': self.contact_id,
            'permission_id': self.permission_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f'<NotificationRule {self.id}>'

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(100))
    is_group = db.Column(db.Boolean, default=False)
    permission = db.relationship('Permission', backref=db.backref('contacts', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'name': self.name,
            'description': self.description,
            'is_group': self.is_group,
            'permission_id': self.permission_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self):
        return f'<Contact {self.name}>'
    
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), index=True)
    dir = db.Column(db.String(120), index=True)    
    permission = db.relationship('Permission', backref=db.backref('documents', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'dir': self.dir,    
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'permission_id': self.permission_id
        }
    
    def __repr__(self):
        return f'<Document {self.title}>'
    
class suMenu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    url = db.Column(db.String(100), default="", nullable=True)
    file = db.Column(db.LargeBinary, default=None, nullable=True) # image
    permission = db.relationship('Permission', backref=db.backref('sumenus', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    
    def __repr__(self):
        return f'<Menu {self.title}>'

# EVENT LISTENERS
# Thread-local storage for session data
from threading import local
_thread_local = local()

@event.listens_for(Session, 'before_commit')
def before_commit_detector(session):
    _thread_local.new = list(session.new)
    _thread_local.dirty = list(session.dirty)
    _thread_local.deleted = list(session.deleted)

@event.listens_for(Session, 'after_commit')
def after_commit_detector(session):
    # logging.info("After commit event for Detector")
    # logging.info(f"Session new: {_thread_local.new}")
    # logging.info(f"Session dirty: {_thread_local.dirty}")
    # logging.info(f"Session deleted: {_thread_local.deleted}")
    from app import detector_manager, socketio
    for obj in _thread_local.new:
        if isinstance(obj, Detector) and 'running' in obj.__dict__:
            socketio.emit('status_update', {'detector_id': obj.id, 'running': obj.running})
            detector_manager.update_detectors()
        if isinstance(obj, CCTV) and 'status' in obj.__dict__:
            socketio.emit('status_update', {'cctv_id': obj.id, 'status': obj.status})
            detector_manager.update_detectors()
    for obj in _thread_local.dirty:
        if isinstance(obj, Detector) and 'running' in obj.__dict__:
            socketio.emit('status_update', {'detector_id': obj.id, 'running': obj.running})
            detector_manager.update_detectors()
        if isinstance(obj, CCTV) and 'status' in obj.__dict__:
            socketio.emit('status_update', {'cctv_id': obj.id, 'status': obj.status})
            detector_manager.update_detectors()
    for obj in _thread_local.deleted:
        if isinstance(obj, Detector):
            socketio.emit('status_update', {'detector_id': obj.id, 'running': False})
            detector_manager.update_detectors()
        if isinstance(obj, CCTV):
            socketio.emit('status_update', {'cctv_id': obj.id, 'status': False})
            detector_manager.update_detectors()

    # Clear thread-local storage after commit
    _thread_local.new = []
    _thread_local.dirty = []
    _thread_local.deleted = []
