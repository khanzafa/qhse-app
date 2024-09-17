from app import create_app
from flask import session

if __name__ == "__main__":
    app = create_app()
    session['permission_id'] = 2
    app.run(debug=True)    
