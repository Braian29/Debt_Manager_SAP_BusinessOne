# get_Data_SAP/get_client_info_function.py
from sesion import cookies, headers
import httpx
import json

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
        try:
            response = httpx.get(url, headers=headers, cookies=cookies, verify=False)
            response.raise_for_status()
            data = response.json()
            all_data.append(data)

            if 'odata.nextLink' in data:
                url = data['odata.nextLink']
            else:
                url = None

        except httpx.RequestError as exc:
            print(f"Error al hacer la solicitud HTTP: {exc}")
            return False
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