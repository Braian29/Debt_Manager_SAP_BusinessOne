# get_Data_SAP/get_invoice_function.py
import httpx
import json
from sesion import cookies, headers
import time

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
        try:
            response = httpx.post(url, headers=headers, cookies=cookies, verify=False, json=data)
            response.raise_for_status()
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

        except httpx.HTTPStatusError as exc:
            print(f"Error al hacer la solicitud HTTP: {exc}")
            print(f"Detalle de la respuesta: {exc.response.text}")
            return False
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
    if get_invoice_data():
        print("El script ha finalizado con éxito.")
    else:
        print("El script ha finalizado con errores.")