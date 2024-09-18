from app import create_app
from flask import session
from user_seeder import seed_users

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)    
