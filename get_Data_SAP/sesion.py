# get_Data_SAP/sesion.py
import httpx
import json
from dotenv import load_dotenv
import os

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
                    env_path = Path(__file__).parent.parent / '.env'
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

company_db = os.getenv("COMPANY_DB")
password = os.getenv("PASSWORD")
username = os.getenv("USERNAME_SAP")
url = os.getenv("URL")
COOKIE_FILE = "cookies.json" # Nombre del archivo para guardar las cookies

headers = {'Content-Type': 'application/json', 'Prefer': 'odata.maxpagesize=10000'}
cookies = None # Inicializamos cookies como None

def get_new_session():
    global cookies # Hacemos cookies global
    data = {"CompanyDB": company_db, "Password": password, "UserName": username}
    try:
        response = httpx.post(url, headers=headers, data=json.dumps(data), verify=False)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        cookies = response.cookies
        print("---------------------------------")
        print("--------Sesión Iniciada----------")
        print("---------------------------------")
        _save_cookies() # Guardar las cookies al obtenerlas
        return True # Return True to confirm a new session was created successfully.
    except httpx.HTTPError as e:
      print(f"Error en la solicitud HTTP: {e}")
      return False # Return False if there is an error when create the new session
    except Exception as e:
        print(f"Error inesperado al obtener la nueva sesión: {e}")
        return False

def _save_cookies():
     # Convierte las cookies a un diccionario antes de guardarlas
    if cookies:
        cookies_dict = {}
        for k, v in cookies.items():
            cookies_dict[k] = v
        with open(COOKIE_FILE, "w") as f:
             json.dump(cookies_dict, f)

def load_cookies():
    try:
        with open(COOKIE_FILE, "r") as f:
            cookies_dict = json.load(f)
            return httpx.Cookies(cookies_dict)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        print("Error: Archivo de cookies corrupto")
        return None

# Initial session creation on startup.
if __name__ == '__main__':
    get_new_session()