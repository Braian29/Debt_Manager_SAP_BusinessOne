#get_Data_SAP\C_load_db.py
import pandas as pd
import sqlite3
from datetime import datetime
import json

def crear_base_datos(nombre_db="mi_base_datos.db"):
    """Crea la base de datos SQLite y las tablas necesarias."""
    conn = sqlite3.connect(nombre_db)
    cursor = conn.cursor()

    # Tabla para clientes con deuda
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes_con_deuda (
            CardCode TEXT PRIMARY KEY,
            CardName TEXT,
            PayTermsGrpCode INTEGER,
            PriceListNum INTEGER,
            SalesPersonCode INTEGER,
            Cellular TEXT,
            EmailAddress TEXT,
            CurrentAccountBalance REAL
        )
    ''')
    
    # Tabla para facturas abiertas (se agregan nuevas columnas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facturas_abiertas (
            CardCode TEXT,
            CardName TEXT,
            DocTotal REAL,
            NumAtCard TEXT,
            DocDate TEXT,
            PaidToDate REAL,
            DocDueDate TEXT,
            DiasDesdeCreacion INTEGER,
            Clasificacion TEXT,
            SaldoPendiente REAL
        )
    ''')
    
    # Tabla para vendedores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendedores (
            SalesEmployeeCode INTEGER PRIMARY KEY,
            SalesEmployeeName TEXT,
            Telephone TEXT,
            Mobile TEXT,
            Email TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
def limpiar_tablas(nombre_db="mi_base_datos.db"):
    """Limpia todas las tablas de la base de datos."""
    conn = sqlite3.connect(nombre_db)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clientes_con_deuda")
    cursor.execute("DELETE FROM facturas_abiertas")
    cursor.execute("DELETE FROM vendedores")
    conn.commit()
    conn.close()

def cargar_clientes_con_deuda(df, nombre_db="mi_base_datos.db"):
    """Carga datos de clientes con deuda desde DataFrame a la base de datos."""
    conn = sqlite3.connect(nombre_db)
    df.to_sql('clientes_con_deuda', conn, if_exists='append', index=False)
    conn.close()

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

def cargar_vendedores(df, nombre_db="mi_base_datos.db"):
    """Carga datos de vendedores desde DataFrame a la base de datos."""
    conn = sqlite3.connect(nombre_db)
    df.to_sql('vendedores', conn, if_exists='append', index=False)
    conn.close()

import pandas as pd
import json

def load_dataframes():
    """
    Carga datos desde archivos JSON y los convierte en DataFrames de pandas,
    filtrando las columnas relevantes para cada tabla.
    
    Returns:
        tuple: Un tuple que contiene tres DataFrames:
               (clientes_df, invoices_df, salespersons_df)
    """
    # Cargar clientes con deuda
    with open('data/clientes_con_deuda.json', 'r') as f:
        clientes_data = json.load(f)

    # Columnas deseadas para clientes
    clientes_columns = ["CardCode", "CardName", "PayTermsGrpCode", "PriceListNum", 
                     "SalesPersonCode", "Cellular", "EmailAddress", "CurrentAccountBalance"]

    # Extraer información de clientes y filtrar columnas
    clientes = pd.json_normalize(clientes_data)
    if 'value' in clientes.columns:
        clientes = pd.json_normalize(clientes_data[0]['value'])
    clientes = clientes[clientes_columns]


    # Cargar facturas abiertas
    with open('data/invoicesAbiertas.json', 'r') as f:
        invoices_data = json.load(f)

    # Columnas deseadas para facturas
    invoices_columns = ["CardCode", "CardName", "DocTotal", "NumAtCard", "DocDate", "PaidToDate", "DocDueDate"]
    
    # Extraer la información de las facturas y filtrar columnas
    invoices = pd.json_normalize([invoice.get('Invoices', {}) for invoice in invoices_data])
    invoices = invoices[invoices_columns]


    # Cargar empleados de ventas
    with open('data/SalesPersons.json', 'r') as f:
        salespersons_data = json.load(f)
    
    # Columnas deseadas para vendedores
    salespersons_columns = ["SalesEmployeeCode", "SalesEmployeeName", "Telephone", "Mobile", "Email"]
    
    # Extraer empleados de ventas y filtrar columnas
    salespersons = pd.json_normalize(salespersons_data)
    if 'value' in salespersons.columns:
       salespersons = pd.json_normalize(salespersons_data[0]['value'])
    salespersons = salespersons[salespersons_columns]

    return clientes, invoices, salespersons

# Función para clasificar las facturas
def clasificar_factura(dias):
    if dias >= 30:
        return 'Vencida'
    elif 20 <= dias <= 29:
        return 'Proxima a Vencer'
    else:
        return 'En Fecha'

def run_load_db():
    # Nombre de la base de datos
    nombre_db = "mi_base_datos.db"

    # Crear base de datos y tablas
    crear_base_datos(nombre_db)

    # Limpiar las tablas
    limpiar_tablas(nombre_db)
    
    # Cargar los dataframes
    clientes_df, invoices_df, salespersons_df = load_dataframes()

    # Procesar el DataFrame de facturas
    invoices_df['DocDate'] = pd.to_datetime(invoices_df['DocDate'])
    today = datetime.now()
    invoices_df['DiasDesdeCreacion'] = (today - invoices_df['DocDate']).dt.days
    invoices_df['Clasificacion'] = invoices_df['DiasDesdeCreacion'].apply(clasificar_factura)
    
    # Cargar datos desde DataFrames
    cargar_clientes_con_deuda(clientes_df, nombre_db)
    cargar_facturas_abiertas(invoices_df, nombre_db)
    cargar_vendedores(salespersons_df, nombre_db)

    print("¡Datos cargados en la base de datos exitosamente!")
    return True

if __name__ == "__main__":
    run_load_db()