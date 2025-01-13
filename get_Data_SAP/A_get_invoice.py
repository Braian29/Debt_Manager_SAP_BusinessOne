# get_Data_SAP/get_invoice_function.py
import httpx
import json
from sesion import cookies, headers, get_new_session
import time

def _make_request(url, method, data=None):
    """Helper function to handle retries and session refresh"""
    max_retries = 2  # Max retries including the first attempt
    for attempt in range(max_retries):
        try:
          
            if method == "POST":
                response = httpx.post(url, headers=headers, cookies=cookies, verify=False, json=data)
            elif method == "GET":
                response = httpx.get(url, headers=headers, cookies=cookies, verify=False)
            else:
                 raise ValueError(f"Invalid HTTP method: {method}")
            response.raise_for_status() # Raise an exception for non 200 status
            return response
        
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401 and attempt < max_retries -1: # 401 Unauthorized, attempt a refresh session
                print("Error de autenticación detectado, intentando refrescar la sesión...")
                if get_new_session(): #Get a new session and try again
                   print("Sesión refrescada con éxito.")
                   continue # Try again after get a new session
                else:
                   print("Fallo al refrescar la sesión")
                   break #Abort if refresh fails
            else:
                print(f"Error al hacer la solicitud HTTP: {exc}")
                print(f"Detalle de la respuesta: {exc.response.text}")
                return None # Return None if is other error or max retries
        except httpx.RequestError as exc:
            print(f"Error al hacer la solicitud HTTP: {exc}")
            return None # Return None if RequestError
        except Exception as exc:
           print(f"Error inesperado: {exc}")
           return None
    print("Máximo número de intentos alcanzados o error irrecuperable.")
    return None

def get_invoice_data(base_url="https://177.85.33.53:50695/b1s/v1/", output_file="data/invoicesAbiertas.json", page_size=1000):
    """
    Obtiene información de facturas abiertas desde la API de SAP y guarda los resultados en un archivo JSON.

    Args:
        base_url (str, opcional): URL base de la API de SAP.
                                 Por defecto: "https://177.85.33.53:50695/b1s/v1/".
        output_file (str, opcional): Ruta del archivo JSON donde se guardarán los datos.
                                    Por defecto: "data/invoicesAbiertas.json".
        page_size (int, opcional): Cantidad de registros por página en la consulta.
                                   Por defecto: 1000.
    Returns:
        bool: True si los datos se obtuvieron y guardaron correctamente, False en caso contrario.
    """

    url = base_url + "QueryService_PostQuery"
    skip = 0
    all_data = []

    while True:
        data = {
            "QueryPath": "$crossjoin(Invoices,BusinessPartners)",
            "QueryOption": f"$expand=Invoices($select=CardCode, CardName, DocTotal, PaidToDate, NumAtCard, DocDate, DocDueDate)&$filter=Invoices/CardCode eq BusinessPartners/CardCode and BusinessPartners/U_Empleado eq 'N' and Invoices/DocumentStatus eq 'O' and BusinessPartners/CurrentAccountBalance gt 10 &$top={page_size}&$skip={skip}"
        }
        print("Enviando datos:")
        print(json.dumps(data, indent=4))

        start_time = time.time()
        response = _make_request(url, "POST", data=data) # Use helper function for the request

        if response is None:
            return False # If is none the request fails
        
        try:
            page_data = response.json()
            end_time = time.time()
            print(f"Petición tardó: {end_time - start_time:.2f} segundos")

            if page_data.get('value'):
                all_data.extend(page_data['value'])
            else:
                break

            if len(page_data['value']) < page_size:
                break
            skip += page_size

        except KeyError as exc:
            print(f"Error al parsear la respuesta JSON: {exc}")
            return False


    if all_data:
        with open(output_file, 'w') as f:
            json.dump(all_data, f, indent=4)
        print("Los datos se han guardado correctamente en el archivo JSON:", output_file)
        return True
    else:
        print("No se obtuvieron datos.")
        return False

if __name__ == '__main__':
    # Ejemplo de uso:
    if get_invoice_data():
        print("El script ha finalizado con éxito.")
    else:
        print("El script ha finalizado con errores.")