#get_Data_SAP\sesion.py
import httpx
import json
from dotenv import load_dotenv
import os

load_dotenv()

company_db = os.getenv("COMPANY_DB")
password = os.getenv("PASSWORD")
username = os.getenv("USERNAME_SAP")
url = os.getenv("URL")

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
        return True # Return True to confirm a new session was created successfully.
    except httpx.HTTPError as e:
      print(f"Error en la solicitud HTTP: {e}")
      return False # Return False if there is an error when create the new session
    except Exception as e:
        print(f"Error inesperado al obtener la nueva sesión: {e}")
        return False

# Initial session creation on startup.
get_new_session()