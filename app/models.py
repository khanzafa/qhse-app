from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    phone_number = db.Column(db.String(20), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(10), default='user')  # 'user' or 'manager'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_manager(self):
        return self.role == 'manager'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone_number': self.phone_number,
            'role': self.role
        }

    def __repr__(self):
        return f'<User {self.name}>'
    
    def get_id(self):
        return str(self.id)
    
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
    
class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(120), index=True, unique=True)
    type = db.Column(db.String(120), index=True)
    ip_address = db.Column(db.String(120), unique=True)
    status = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'location': self.location,
            'type': self.type,
            'ip_address': self.ip_address,
            'status': self.status
        }
    
    def __repr__(self):
        return f'<Camera {self.location}>'

class Detector(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'))
    camera = db.relationship('Camera', backref=db.backref('detector', uselist=False))
    detector_type = db.relationship('DetectorType', backref=db.backref('detector', uselist=False))
    detector_type_id = db.Column(db.Integer, db.ForeignKey('detector_type.id'))
    weight = db.relationship('Weight', backref=db.backref('detector', uselist=False))
    weight_id = db.Column(db.Integer, db.ForeignKey('weight.id'))
    running = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'detector_type_id': self.detector_type_id,
            'running': self.running
        }
    
    def __repr__(self):
        return f'<Detector {self.id}>'

class DetectorType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True, unique=True)
    description = db.Column(db.String(120))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
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

    def to_dict(self):
        return {
            'id': self.id,
            'detector_id': self.detector_id,
            'name': self.name,
            'frame': self.frame,
            'timestamp': self.timestamp
        }

    def __repr__(self):
        return f'<DetectedObject {self.id}>'    

class Weight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    file = db.Column(db.LargeBinary)    
    path = db.Column(db.String(120), index=True)
    detector_type = db.relationship('DetectorType', backref=db.backref('weights', lazy=True))
    detector_type_id = db.Column(db.Integer, db.ForeignKey('detector_type.id'))
    created_at = db.Column(db.DateTime, index=True)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))  # Ganti 'description' dengan 'name'

    def to_dict(self):
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'name': self.name
        }

    def __repr__(self):
        return f'<Contact {self.phone_number}>'

class GroupContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status
        }
    
    def __repr__(self):
        return f'<GroupContact {self.name}>'
    
class suMenu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    url = db.Column(db.String(100), default=True, nullable=False)
    file = db.Column(db.LargeBinary) # image
    path = db.Column(db.String(120), index=True)
    
    def __repr__(self):
        return f'<GroupContact {self.name}>'