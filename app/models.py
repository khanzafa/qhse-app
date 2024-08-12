from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    phone_number = db.Column(db.String(20), index=True, unique=True)

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
    type = db.Column(db.String(120), index=True)
    running = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'type': self.type,
            'running': self.running
        }

    def __repr__(self):
        return f'<Detector {self.camera_id}>'
    
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

