import httpx
import json
from dotenv import load_dotenv
import os

# Carga las variables del archivo .env
load_dotenv()

# Obtén las variables de entorno
company_db = os.getenv("COMPANY_DB")
password = os.getenv("PASSWORD")
username = os.getenv("USERNAME_SAP")
url = os.getenv("URL")

# Inicio de Sesión
headers = {'Content-Type': 'application/json', 'Prefer': 'odata.maxpagesize=10000'}
data = {"CompanyDB": company_db, "Password": password, "UserName": username}
response = httpx.post(url, headers=headers, data=json.dumps(data), verify=False)

if response.status_code == 200:   # Inicio de sesión exitoso
    print("---------------------------------")
    print("--------Sesión Iniciada----------")
    print("---------------------------------")
    cookies = response.cookies
else:                             # Inicio de sesión fallido
    print(response.text)