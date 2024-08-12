import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://myuser:mypassword@localhost/mydatabase'
    SQLALCHEMY_TRACK_MODIFICATIONS = False    

    # Konfigurasi API WhatsApp
    WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL') or 'https://api.whatsapp.com/send'
    WHATSAPP_API_KEY = os.environ.get('WHATSAPP_API_KEY') or 'your-whatsapp-api-key'
