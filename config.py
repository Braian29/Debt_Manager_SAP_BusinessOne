# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Obtener la ruta absoluta al directorio del script actual
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'mi_base_datos.db')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DATABASE_PATH.replace('\\', '/')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = os.getenv('MAIL_PORT')