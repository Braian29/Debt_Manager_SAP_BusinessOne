# get_Data_SAP/get_client_info_function.py
import httpx
import json
from get_Data_SAP import sesion # Importar sesion como modulo

def _make_request(url, method, data=None):
    """Helper function to handle retries and session refresh"""
    max_retries = 2  # Max retries including the first attempt
    for attempt in range(max_retries):
        cookies = sesion.load_cookies() # Obtener las cookies antes de cada intento
        if cookies is None:
            print("No se pudieron cargar las cookies. Saliendo.")
            return None # Break if cannot get cookies.

        try:
             headers = {'Content-Type': 'application/json', 'Prefer': 'odata.maxpagesize=10000'} # Se inicializa aqui por si se usa diferente headers

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
                if sesion.get_new_session(): #Get a new session and try again
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

def get_client_data(base_url="https://177.85.33.53:50695/b1s/v1/", output_file="data/clientes_con_deuda.json"):
    """
    Obtiene información de clientes con deuda desde la API de SAP y guarda los resultados en un archivo JSON.

    Args:
        base_url (str, opcional): URL base de la API de SAP. 
                                 Por defecto: "https://177.85.33.53:50695/b1s/v1/".
        output_file (str, opcional): Ruta del archivo JSON donde se guardarán los datos.
                                    Por defecto: "data/clientes_con_deuda.json".

    Returns:
        bool: True si los datos se obtuvieron y guardaron correctamente, False en caso contrario.
    """

    url = base_url + "BusinessPartners?$select=CardCode,CardName,PayTermsGrpCode,PriceListNum,SalesPersonCode,Cellular,EmailAddress,CurrentAccountBalance&$filter=CurrentAccountBalance gt 1000 and CardType eq 'cCustomer' and U_Empleado eq 'N'"
    all_data = []

    while url:
        response = _make_request(url, "GET") # Use helper function for the request

        if response is None:
           return False # If the request fails

        try:
            data = response.json()
            all_data.append(data)

            if 'odata.nextLink' in data:
                url = data['odata.nextLink']
            else:
                url = None
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
    if get_client_data():
        print("El script ha finalizado con éxito.")
    else:
        print("El script ha finalizado con errores.")