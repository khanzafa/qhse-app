from app import app
from flask import session

if __name__ == "__main__":
    app.run(debug=True)
    session['permission_id'] = 2