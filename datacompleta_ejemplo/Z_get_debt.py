import httpx
import pandas as pd

# Supongo que 'cookies' y 'headers' están definidos en 'sesion.py'
from get_Data_SAP.sesion import cookies, headers

def obtener_y_procesar_datos(card_code):
    """
    Obtiene datos de una API, los procesa y devuelve un DataFrame.

    Args:
        card_code (int): El código de tarjeta para la consulta.

    Returns:
        pandas.DataFrame: Un DataFrame con los datos filtrados, o None si hay un error.
    """

    base_url = "https://177.85.33.53:50695/b1s/v1/"
    url = f"https://177.85.33.53:50695/b1s/v1/sml.svc/ScriptViewBalanceParameters('''{card_code}''')/ScriptViewBalance"
    all_data = []

    while url:
        try:
            response = httpx.get(url, headers=headers, cookies=cookies, verify=False)
            response.raise_for_status()  # Lanza una excepción si el status code no es 200

            data = response.json()
            all_data.extend(data['value'])
            next_link = data.get('odata.nextLink')
            if next_link:
                url = base_url + next_link
            else:
                url = None
        except httpx.HTTPError as e:
            print(f"Error al obtener datos: {e}")
            return None  # Sale de la función en caso de error
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None  # Sale de la función en caso de error

    # Convertir la lista de diccionarios a un DataFrame
    if all_data:
        balance_data = pd.DataFrame(all_data)
        balance_data = balance_data[['RefDate', 'Debit', 'Credit', 'CalcSubType', 'PTICode', 'Letter', 'FolNumFrom']]
        balance_data['CardCode'] = CardCode
        return balance_data
    else:
        return None

# Ejemplo de uso:
if __name__ == "__main__":
    CardCode = 20005
    balance_df = obtener_y_procesar_datos(CardCode)

    if balance_df is not None:
        print(balance_df)