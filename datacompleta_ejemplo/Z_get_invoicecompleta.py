# 
from sesion import cookies, headers
import httpx
import json

def get_invoices_data(base_url="https://177.85.33.53:50695/b1s/v1/", output_file="datacompleta_ejemplo/InvoiceCompleto.json"):
    url = base_url + "Invoices?$filter=DocEntry eq 1547215"
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
    if get_invoices_data():
        print("El script ha finalizado con éxito.")
    else:
        print("El script ha finalizado con errores.")