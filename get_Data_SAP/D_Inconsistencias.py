import sqlite3
import pandas as pd
import httpx
import json
from sesion import cookies, headers
import time


def encontrar_clientes_sin_factura(nombre_db="mi_base_datos.db"):
    """
    Encuentra clientes que están en la tabla clientes_con_deuda pero no tienen facturas en facturas_abiertas.

    Args:
        nombre_db (str, optional): El nombre de la base de datos SQLite. 
                                   Por defecto: "mi_base_datos.db".

    Returns:
        list: Una lista de CardCode de clientes que no tienen facturas.
              Retorna una lista vacía si no hay clientes sin factura o si hay un error.
    """
    conn = None
    try:
        conn = sqlite3.connect(nombre_db)
        cursor = conn.cursor()

        # Obtener todos los CardCode de la tabla de clientes
        cursor.execute("SELECT CardCode FROM clientes_con_deuda")
        clientes_cardcodes = set(row[0] for row in cursor.fetchall())

        # Obtener todos los CardCode de la tabla de facturas
        cursor.execute("SELECT CardCode FROM facturas_abiertas")
        facturas_cardcodes = set(row[0] for row in cursor.fetchall())

        # Encontrar los CardCode de los clientes que no están en facturas
        clientes_sin_factura = list(clientes_cardcodes - facturas_cardcodes)

        return clientes_sin_factura

    except sqlite3.Error as e:
        print(f"Error de SQLite: {e}")
        return []
    finally:
        if conn:
            conn.close()


def obtener_informacion_clientes_sin_factura(nombre_db="mi_base_datos.db"):
    """
    Obtiene información detallada de los clientes que no tienen facturas.

    Args:
        nombre_db (str, optional): El nombre de la base de datos SQLite.
                                   Por defecto: "mi_base_datos.db".

    Returns:
        pandas.DataFrame: Un DataFrame con la información de los clientes sin facturas, o un DataFrame vacío si no hay datos o hay un error.
    """
    clientes_sin_factura_cardcodes = encontrar_clientes_sin_factura(nombre_db)

    if not clientes_sin_factura_cardcodes:
        print("No se encontraron clientes sin facturas o hubo un error al obtener los datos.")
        return pd.DataFrame()

    conn = None
    try:
        conn = sqlite3.connect(nombre_db)
        query = "SELECT * FROM clientes_con_deuda WHERE CardCode IN ({})".format(
            ','.join('?' * len(clientes_sin_factura_cardcodes))
        )
        df = pd.read_sql_query(query, conn, params=clientes_sin_factura_cardcodes)
        return df
    except sqlite3.Error as e:
        print(f"Error de SQLite: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_invoice_data(base_url="https://177.85.33.53:50695/b1s/v1/", page_size=1000, specific_cardcode=None):
    """
    Obtiene información de facturas abiertas desde la API de SAP, filtrando por un CardCode específico.

    Args:
        base_url (str, opcional): URL base de la API de SAP.
                                 Por defecto: "https://177.85.33.53:50695/b1s/v1/".
        page_size (int, opcional): Cantidad de registros por página en la consulta.
                                   Por defecto: 1000.
        specific_cardcode (str, optional): CardCode para filtrar la consulta. Si es None, se obtienen todas las facturas. Por defecto: None.
    Returns:
         list: Una lista con los datos obtenidos o una lista vacía en caso de error o sin datos.
    """
    url = base_url + "QueryService_PostQuery"
    skip = 0
    all_data = []

    if not specific_cardcode:
        print("Error: specific_cardcode es requerido para esta función")
        return []

    while True:
        data = {
            "QueryPath": "$crossjoin(Invoices,BusinessPartners)",
            "QueryOption": f"$expand=Invoices($select=CardCode, CardName, DocTotal, PaidToDate, NumAtCard, DocDate, DocDueDate)&$filter=Invoices/CardCode eq BusinessPartners/CardCode and BusinessPartners/Valid eq 'Y' and BusinessPartners/U_Empleado eq 'N' and Invoices/DocumentStatus eq 'O' and BusinessPartners/CurrentAccountBalance gt 10 and Invoices/CardCode eq '{specific_cardcode}'&$top={page_size}&$skip={skip}"
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
            return []
        except httpx.RequestError as exc:
            print(f"Error al hacer la solicitud HTTP: {exc}")
            return []
        except KeyError as exc:
            print(f"Error al parsear la respuesta JSON: {exc}")
            return []

    return all_data

def cargar_facturas_abiertas(df, nombre_db="mi_base_datos.db"):
    """Carga datos de facturas abiertas desde DataFrame a la base de datos."""
    conn = sqlite3.connect(nombre_db)
    
    # Convertir DocDate a Datetime
    df['DocDate'] = pd.to_datetime(df['DocDate'])
    
    # Convertir PaidToDate a numérico, si no puede convertir, asignarle cero
    df['PaidToDate'] = pd.to_numeric(df['PaidToDate'], errors='coerce').fillna(0)
    
    # Calcular el saldo pendiente
    df['SaldoPendiente'] = df['DocTotal'] - df['PaidToDate']
    
    df.to_sql('facturas_abiertas', conn, if_exists='append', index=False)
    conn.close()


def run_find_inconsistencies():
    """Ejecuta la lógica para encontrar inconsistencias y actualizar la base de datos."""
    
    nombre_db = "mi_base_datos.db"
    
    # Encuentra clientes sin facturas
    clientes_sin_factura_cardcodes = encontrar_clientes_sin_factura(nombre_db)
    
    if clientes_sin_factura_cardcodes:
        print("Clientes (CardCode) sin facturas abiertas:")
        for cardcode in clientes_sin_factura_cardcodes:
            print(cardcode)

        # Ahora obtenemos la información completa de esos clientes:
        df_clientes_sin_factura = obtener_informacion_clientes_sin_factura(nombre_db)
        if not df_clientes_sin_factura.empty:
            print("\nInformación detallada de los clientes sin facturas:")
            print(df_clientes_sin_factura)
        else:
            print("\nNo se pudo obtener la información detallada de los clientes sin facturas.")
        
        all_invoices_data = []
        # Volvemos a obtener las facturas solo para estos clientes,  llamando a get_invoice_data() individualmente
        print("\nVolviendo a obtener facturas para los clientes sin facturas...")
        for cardcode in clientes_sin_factura_cardcodes:
            print(f"Obteniendo facturas para el cliente: {cardcode}")
            invoices_data = get_invoice_data(specific_cardcode=cardcode)
            if invoices_data:
                all_invoices_data.extend(invoices_data)

        if all_invoices_data:
            print("Facturas obtenidas exitosamente.")
            # Convertir la lista de datos de facturas en un DataFrame
            invoices_columns = ["CardCode", "CardName", "DocTotal", "NumAtCard", "DocDate", "PaidToDate", "DocDueDate"]
            invoices = pd.json_normalize([invoice.get('Invoices', {}) for invoice in all_invoices_data])
            invoices = invoices[invoices_columns]

             # Actualizar la tabla facturas_abiertas con las nuevas facturas
            cargar_facturas_abiertas(invoices, nombre_db)
            print("Tabla de facturas actualizada con nuevos datos.")
        
        else:
             print("No se encontraron facturas para los clientes sin facturas.")
    else:
        print("No se encontraron clientes sin facturas abiertas.")


if __name__ == "__main__":
    # Primero, asegúrate de que la base de datos esté cargada. (ejecuta Z_run_scripts.py antes)
    run_find_inconsistencies()