import asyncio
import httpx
import pandas as pd
import json
import time

# Supongo que 'cookies' y 'headers' están definidos en 'sesion.py'
from get_Data_SAP.sesion import cookies, headers

async def obtener_y_procesar_datos(client, card_code, max_retries=3, initial_delay=1):
    """
    Obtiene datos de una API asíncronamente para un CardCode específico, con reintentos en caso de timeout.

    Args:
        client (httpx.AsyncClient): Cliente HTTP asíncrono.
        card_code (str): El código de tarjeta para la consulta.
        max_retries (int): Número máximo de reintentos.
        initial_delay (int): Tiempo de espera inicial en segundos para el primer reintento.

    Returns:
        pandas.DataFrame: Un DataFrame con los datos filtrados, o None si hay un error.
    """
    base_url = "https://177.85.33.53:50695/b1s/v1/"
    url = f"https://177.85.33.53:50695/b1s/v1/sml.svc/ScriptViewBalanceParameters('''{card_code}''')/ScriptViewBalance"
    all_data = []

    for attempt in range(max_retries):
        try:
            response = await client.get(url, headers=headers, cookies=cookies, timeout=30)
            response.raise_for_status()
            data = response.json()
            all_data.extend(data.get('value', []))
            next_link = data.get('odata.nextLink')
            if next_link:
                url = base_url + next_link
            else:
                url = None
            break # Si la solicitud fue exitosa, sal del bucle de reintentos
        except httpx.HTTPError as e:
            if isinstance(e, httpx.ReadTimeout):
                delay = initial_delay * (2 ** attempt)
                print(f"Error ReadTimeout al obtener datos para {card_code}, reintento {attempt + 1}/{max_retries}, en {delay} segundos.")
                await asyncio.sleep(delay)
                continue # Si es un timeout, espera y reintenta.
            elif hasattr(e, 'response'):
                print(f"Error HTTP al obtener datos para {card_code}: {e} - Status: {e.response.status_code}, Reason: {e.response.reason_phrase}")
            else:
                print(f"Error desconocido al obtener datos para {card_code}: {e}")
            return None # Si es otro error HTTP, no reintenta y sale de la función.
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON para {card_code}: {e}")
            return None # Si es error de decodificación JSON, sale.
        except Exception as e:
           print(f"Error inesperado al obtener datos para {card_code}: {e}")
           return None

    # Convertir la lista de diccionarios a un DataFrame
    if all_data:
        balance_data = pd.DataFrame(all_data)
        balance_data = balance_data[['RefDate', 'Debit', 'Credit', 'CalcSubType', 'PTICode', 'Letter', 'FolNumFrom']]
        balance_data['CardCode'] = card_code # Usamos el card_code que se paso a la funcion
        return balance_data
    else:
        print(f"No se encontraron datos para CardCode: {card_code}")
        return None



async def obtener_datos_multiples_cardcodes(cardcodes_path):
    """
    Lee una lista de CardCodes desde un archivo JSON y obtiene y procesa datos para cada uno de forma asíncrona.

    Args:
        cardcodes_path (str): La ruta al archivo JSON con la lista de CardCodes.

    Returns:
        pandas.DataFrame: Un DataFrame con los datos de todos los CardCodes, o None si hay un error.
    """
    try:
        with open(cardcodes_path, 'r') as f:
            card_codes = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {cardcodes_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: No se puede decodificar el archivo JSON {cardcodes_path}")
        return None

    async with httpx.AsyncClient(verify=False) as client: # Configuración del cliente con verify=False
      tasks = [obtener_y_procesar_datos(client, card_code) for card_code in card_codes]
      results = await asyncio.gather(*tasks)

    all_dfs = [df for df in results if df is not None]
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    else:
        return None


# Ejemplo de uso:
async def main():
    cardcodes_file = "data/CardCodes.json"
    all_data_df = await obtener_datos_multiples_cardcodes(cardcodes_file)

    if all_data_df is not None:
        print(all_data_df)
        all_data_df.to_excel('data/output.xlsx', index=False) # Puedes agregar esto para guardar el dataframe
    else:
        print("No se obtuvieron datos para ninguno de los CardCodes.")

if __name__ == "__main__":
    asyncio.run(main())