from datetime import datetime
import cv2
from ultralytics import YOLO
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

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

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    phone_number = db.Column(db.String(20), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(10), default='user')
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # def is_manager(self):
    #     return self.role == 'manager'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('user_permissions', lazy=True))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
    permission = db.relationship('Permission', backref=db.backref('user_permissions', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'permission_id': self.permission_id
        }
    
    def __repr__(self):
        return f'<UserPermission {self.id}>'
        
class CCTV(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(120), index=True, unique=True)
    type = db.Column(db.String(120), index=True)
    ip_address = db.Column(db.String(120))
    status = db.Column(db.Boolean, default=False)
    permission = db.relationship('Permission', backref=db.backref('cctvs', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
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

class Detector(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cctv_id = db.Column(db.Integer, db.ForeignKey('cctv.id'))
    cctv = db.relationship('CCTV', backref=db.backref('detectors', uselist=False))
    detector_type = db.relationship('DetectorType', backref=db.backref('detectors', uselist=False))
    detector_type_id = db.Column(db.Integer, db.ForeignKey('detector_type.id'))
    weight = db.relationship('Weight', backref=db.backref('detectors', uselist=False))
    weight_id = db.Column(db.Integer, db.ForeignKey('weight.id'))
    running = db.Column(db.Boolean, default=False)
    permission = db.relationship('Permission', backref=db.backref('detectors', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

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
    
    def process_frame(self, frame):
        model = YOLO(self.weight.path)
        results = model.track(frame, stream=False, persist=True)
        detected_objects = []
        for c in results[0].boxes:
            track_id = c.id if hasattr(c, 'id') else None
            track_id = int(track_id.item())  # Convert from tensor to int
            class_id = c.cls
            name = self.model.names[int(class_id)]
            detected_object = DetectedObject(
                detector_id=self.id,
                name=name,
                frame=cv2.imencode('.jpg', frame)[1].tobytes(),
                timestamp=datetime.now(),
                permission_id=self.permission_id                
            )
            detected_objects.append(detected_object)
            db.session.add(detected_object)
            db.session.commit()
            
        return detected_objects
        

class DetectorType(db.Model):
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
        return f'<DetectorType {self.name}>'

class DetectedObject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    detector = db.relationship('Detector', backref=db.backref('detected_objects', lazy=True))
    detector_id = db.Column(db.Integer, db.ForeignKey('detector.id'))
    name = db.Column(db.String(120), index=True)
    frame = db.Column(db.LargeBinary)
    timestamp = db.Column(db.DateTime, index=True)
    permission = db.relationship('Permission', backref=db.backref('detected_objects', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
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
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
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
    detector_id = db.Column(db.Integer, db.ForeignKey('detector.id'))
    detector = db.relationship('Detector', backref=db.backref('notification_rules', lazy=True))
    message_template_id = db.Column(db.Integer, db.ForeignKey('message_template.id'))
    message_template = db.relationship('MessageTemplate', backref=db.backref('notification_rules', lazy=True))
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    contact = db.relationship('Contact', backref=db.backref('notification_rules', lazy=True))
    permission = db.relationship('Permission', backref=db.backref('notification_rules', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
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

class Weight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    file = db.Column(db.LargeBinary)    
    path = db.Column(db.String(120), index=True)
    detector_type = db.relationship('DetectorType', backref=db.backref('weights', lazy=True))
    detector_type_id = db.Column(db.Integer, db.ForeignKey('detector_type.id'))
    created_at = db.Column(db.DateTime, index=True)
    permission = db.relationship('Permission', backref=db.backref('weights', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(100))
    is_group = db.Column(db.Boolean, default=False)
    permission = db.relationship('Permission', backref=db.backref('contacts', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
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
    file = db.Column(db.LargeBinary)
    permission = db.relationship('Permission', backref=db.backref('documents', uselist=False))
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
    created_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, index=True, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'dir': self.dir,
            'file': self.file,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'permission_id': self.permission_id
        }
    
    def __repr__(self):
        return f'<Document {self.title}>'
    
class suMenu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    url = db.Column(db.String(100), default=True, nullable=False)
    file = db.Column(db.LargeBinary) # image
    path = db.Column(db.String(120), index=True)
    
    def __repr__(self):
        return f'<GroupContact {self.name}>'
