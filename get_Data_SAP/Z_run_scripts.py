#get_Data_SAP\Z_run_scripts.py
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__)) # Obtener el directorio actual de Z_run_scripts.py
sys.path.append(current_dir) # Agregar el directorio actual al path de Python

from B_get_allinfo import run_get_allinfo
from C_load_db import run_load_db


def run_scripts():
    """Ejecuta los scripts de obtención y carga de datos en secuencia."""
    
    try:
        # Ejecutamos el primer script (B_get_allinfo.py)
        print("Ejecutando B_get_allinfo.py...")
        if run_get_allinfo():
            print("B_get_allinfo.py ejecutado correctamente.")
        else:
            print("Error en la ejecución de B_get_allinfo.py")
            return False #Detenemos la ejecución si hubo un error
       
        # Ejecutamos el segundo script (C_load_db.py)
        print("Ejecutando C_load_db.py...")
        if run_load_db():
            print("C_load_db.py ejecutado correctamente.")
            return True
        else:
            print("Error en la ejecución de C_load_db.py")
            return False #Detenemos la ejecución si hubo un error
    except Exception as e:
         print(f"Error inesperado: {e}")
         return False

if __name__ == '__main__':
    if run_scripts():
        print("Actualización completa de la base de datos exitosa.")
    else:
        print("La actualización de la base de datos ha fallado.")