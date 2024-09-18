from flask import current_app
from app import db
from app.models import User
from faker import Faker
import random

fake = Faker()

def seed_users(n):
    for _ in range(n):
        name = fake.name()
        phone_number = fake.unique.phone_number()
        password = fake.password()
        
        # Random role between 'user', 'admin', 'manager'
        role = random.choice(['user', 'admin', 'manager'])

        # Randomly approve users (None or True)
        approved = random.choice([None, True])

        user = User(
            name=name,
            phone_number=phone_number,
            role=role,
            approved=approved
        )
        user.set_password(password)

        db.session.add(user)

    db.session.commit()
    print(f'{n} users added successfully!')
