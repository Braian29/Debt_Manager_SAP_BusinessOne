# config.py
import os
from dotenv import load_dotenv

# Función helper para cargar .env con diferentes codificaciones
def load_env_with_encoding():
    """Intenta cargar el archivo .env con diferentes codificaciones"""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for encoding in encodings:
        try:
            load_dotenv(encoding=encoding)
            return
        except (UnicodeDecodeError, TypeError):
            # Si encoding no está disponible o falla, intentar manualmente
            try:
                from pathlib import Path
                env_path = Path('.env')
                if not env_path.exists():
                    env_path = Path(__file__).parent / '.env'
                if env_path.exists():
                    with open(env_path, 'r', encoding=encoding) as f:
                        for line in f:
                            line = line.strip()
                            if line and '=' in line and not line.startswith('#'):
                                key, value = line.split('=', 1)
                                os.environ[key.strip()] = value.strip().strip('"\'')
                    return
            except Exception:
                continue
    # Si todas fallan, intentar sin especificar encoding
    try:
        load_dotenv()
    except Exception:
        pass

load_env_with_encoding()

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