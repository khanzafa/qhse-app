import random
from faker import Faker
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.models import CCTVLocation, CCTV, Weight, Detector, DetectorType, DetectedObject, MessageTemplate, NotificationRule, Contact, Permission, UserPermission, User, UserRole, suMenu
from app.extensions import db

app = Flask(__name__)
app.config.from_object('config.Config')
faker = Faker()
db.init_app(app)

# Permission ID yang digunakan
PERMISSION_ID = 2

# Fungsi untuk membuat data dummy
def seed_admin():
    admin = User(
        name="Admin",
        email="admin@spil.co.id",
        phone_number="682199765213",
        role=UserRole.admin,
        approved=True,        
    )
    
def seed_users(n):
    for _ in range(n):
        user = User(
            name=faker.name(),
            email=faker.unique.email(),
            phone_number=faker.phone_number(),
            role=random.choice([UserRole.user, UserRole.admin, UserRole.guest]),
            approved=False
        )
        db.session.add(user)
    db.session.commit()

def seed_permissions(n):
    qhse = Permission(
        name="QHSE",
        description="Quality, Health, Safety, and Environment"
    )
    paier = Permission(
        name="PAIER",
        description="Public Affairs, Industrial, and Employee Relations"
    )
    db.session.add(qhse)
    db.session.add(paier)

    for _ in range(n):
        permission = Permission(
            name=faker.word(),
            description=faker.text(max_nb_chars=120)
        )
        db.session.add(permission)
    db.session.commit()

def seed_user_permissions(n):
    users = User.query.all()
    permissions = Permission.query.all()
    for _ in range(n):
        user_permission = UserPermission(
            user_id=random.choice(users).id,
            permission_id=random.choice(permissions).id
        )
        db.session.add(user_permission)
    db.session.commit()

def seed_menus(n):
    chatbot = suMenu(
        title="Chatbot",
        url="/guide-bot/chat",
        permission_id=PERMISSION_ID
    )
    shift_bko = suMenu(
        title="Shift and BKO Reccomendation",
        url="/shift-bko",
        permission_id=PERMISSION_ID
    )
    db.session.add(chatbot)
    db.session.add(shift_bko)
    permissions = Permission.query.all()
    for _ in range(n):
        menu = suMenu(
            title=faker.word(),
            url=faker.url(),
            permission_id=random.choice(permissions).id
        )
        db.session.add(menu)
    db.session.commit()

def seed_cctv_locations(n):
    for _ in range(n):
        location = CCTVLocation(
            name=faker.city(),
            description=faker.text(max_nb_chars=120)
        )
        db.session.add(location)
    db.session.commit()

def seed_cctvs(n):
    locations = CCTVLocation.query.all()
    for _ in range(n):
        cctv = CCTV(
            cctv_location_id=random.choice(locations).id,
            type=faker.word(),
            ip_address=faker.ipv4(),
            status=random.choice([True, False]),
            permission_id=PERMISSION_ID
        )
        db.session.add(cctv)
    db.session.commit()

def seed_detector_types(n):
    for _ in range(n):
        detector_type = DetectorType(
            name=faker.word(),
            description=faker.text(max_nb_chars=120),
        )
        db.session.add(detector_type)
    db.session.commit()

def seed_weights(n):
    detector_types = DetectorType.query.all()
    for _ in range(n):
        weight = Weight(
            name=faker.word(),
            file=faker.binary(length=512),  # Menggunakan binary data acak
            path=faker.file_path(),
            detector_type_id=random.choice(detector_types).id,
            permission_id=PERMISSION_ID
        )
        db.session.add(weight)
    db.session.commit()

def seed_detectors(n):
    cctvs = CCTV.query.all()
    detector_types = DetectorType.query.all()
    weights = Weight.query.all()
    for _ in range(n):
        detector = Detector(
            cctv_id=random.choice(cctvs).id,
            detector_type_id=random.choice(detector_types).id,
            weight_id=random.choice(weights).id,
            running=random.choice([True, False]),
            permission_id=PERMISSION_ID
        )
        db.session.add(detector)
    db.session.commit()

def seed_detected_objects(n):
    detectors = Detector.query.all()
    for _ in range(n):
        detected_object = DetectedObject(
            detector_id=random.choice(detectors).id,
            name=faker.word(),
            frame=faker.binary(length=1024),  # Menggunakan binary data acak
            timestamp=faker.date_time_this_year(),
            permission_id=PERMISSION_ID
        )
        db.session.add(detected_object)
    db.session.commit()

def seed_message_templates(n):
    for _ in range(n):
        template = MessageTemplate(
            name=faker.word(),
            template=faker.text(max_nb_chars=480),
            permission_id=PERMISSION_ID
        )
        db.session.add(template)
    db.session.commit()

def seed_notification_rules(n):
    detectors = Detector.query.all()
    message_templates = MessageTemplate.query.all()
    contacts = Contact.query.all()
    for _ in range(n):
        notification_rule = NotificationRule(
            detector_id=random.choice(detectors).id,
            message_template_id=random.choice(message_templates).id,
            contact_id=random.choice(contacts).id,
            permission_id=PERMISSION_ID
        )
        db.session.add(notification_rule)
    db.session.commit()

def seed_contacts(n):
    for _ in range(n):
        contact = Contact(
            phone_number=faker.phone_number(),
            name=faker.name(),
            description=faker.text(max_nb_chars=100),
            is_group=random.choice([True, False]),
            permission_id=PERMISSION_ID
        )
        db.session.add(contact)
    db.session.commit()

# Menjalankan seeder
def run_seeders():
    print("Seeding Admin...")
    seed_admin()

    print("Seeding Users...")
    seed_users(5)

    print("Seeding Permissions...")
    seed_permissions(5) 

    # print("Seeding User Permissions...")
    # seed_user_permissions(30)

    print("Seeding Menus...")
    seed_menus(10)

    # print("Seeding CCTV Locations...")
    # seed_cctv_locations(5)

    # print("Seeding CCTVs...")
    # seed_cctvs(5)

    # print("Seeding Detector Types...")
    # seed_detector_types(5)

    # print("Seeding Weights...")
    # seed_weights(10)

    # print("Seeding Detectors...")
    # seed_detectors(10)

    # print("Seeding Detected Objects...")
    # seed_detected_objects(100)

    # print("Seeding Message Templates...")
    # seed_message_templates(10)

    # print("Seeding Contacts...")
    # seed_contacts(5)

    # print("Seeding Notification Rules...")
    # seed_notification_rules(10)

if __name__ == '__main__':
    with app.app_context():   
        run_seeders()
