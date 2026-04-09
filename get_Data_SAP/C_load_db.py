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

def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_odata_value(payload):
    """
    Algunos endpoints se guardan como lista con un objeto que contiene `value`.
    Soporta:
    - {"value": [...]}
    - [{"value": [...]}]
    - [...]
    """
    if isinstance(payload, dict) and "value" in payload:
        return payload["value"]
    if isinstance(payload, list) and payload and isinstance(payload[0], dict) and "value" in payload[0]:
        return payload[0]["value"]
    return payload


def _to_float(v, default=0.0):
    try:
        if v is None or v == "":
            return float(default)
        return float(v)
    except (ValueError, TypeError):
        return float(default)


def _to_int(v, default=None):
    try:
        if v is None or v == "":
            return default
        return int(v)
    except (ValueError, TypeError):
        return default


def _parse_date(date_str):
    """
    SAP suele devolver ISO 8601. Aceptamos:
    - 'YYYY-MM-DD'
    - 'YYYY-MM-DDTHH:MM:SS...'
    """
    if not date_str:
        return None
    try:
        # Python 3.11+: fromisoformat soporta 'YYYY-MM-DD' y 'YYYY-MM-DDTHH:MM:SS'
        return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
    except Exception:
        # fallback simple
        try:
            return datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        except Exception:
            return None


def load_rows():
    """
    Lee JSONs y devuelve filas listas para insertar en SQLite:
    - clientes_rows
    - facturas_rows
    - vendedores_rows
    """
    clientes_payload = _read_json("data/clientes_con_deuda.json")
    clientes = _extract_odata_value(clientes_payload) or []

    vendedores_payload = _read_json("data/SalesPersons.json")
    vendedores = _extract_odata_value(vendedores_payload) or []

    invoices_payload = _read_json("data/invoicesAbiertas.json")
    invoices = invoices_payload or []

    clientes_rows = []
    for c in clientes:
        clientes_rows.append(
            (
                c.get("CardCode"),
                c.get("CardName"),
                _to_int(c.get("PayTermsGrpCode")),
                _to_int(c.get("PriceListNum")),
                _to_int(c.get("SalesPersonCode")),
                c.get("Cellular"),
                c.get("EmailAddress"),
                _to_float(c.get("CurrentAccountBalance")),
            )
        )

    vendedores_rows = []
    for v in vendedores:
        vendedores_rows.append(
            (
                _to_int(v.get("SalesEmployeeCode")),
                v.get("SalesEmployeeName"),
                v.get("Telephone"),
                v.get("Mobile"),
                v.get("Email"),
            )
        )

    today = datetime.now()
    facturas_rows = []
    for item in invoices:
        inv = item.get("Invoices", {}) if isinstance(item, dict) else {}
        card_code = inv.get("CardCode")
        card_name = inv.get("CardName")
        doc_total = _to_float(inv.get("DocTotal"))
        paid_to_date = _to_float(inv.get("PaidToDate"))
        saldo_pendiente = doc_total - paid_to_date

        doc_date_raw = inv.get("DocDate")
        doc_date_dt = _parse_date(doc_date_raw)
        dias = (today - doc_date_dt).days if doc_date_dt else None
        clasificacion = clasificar_factura(dias) if dias is not None else None

        facturas_rows.append(
            (
                card_code,
                card_name,
                doc_total,
                inv.get("NumAtCard"),
                str(doc_date_raw) if doc_date_raw is not None else None,
                paid_to_date,
                inv.get("DocDueDate"),
                dias,
                clasificacion,
                saldo_pendiente,
            )
        )

    return clientes_rows, facturas_rows, vendedores_rows

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
    
    clientes_rows, facturas_rows, vendedores_rows = load_rows()

    conn = sqlite3.connect(nombre_db)
    cur = conn.cursor()

    cur.executemany(
        """
        INSERT INTO clientes_con_deuda
        (CardCode, CardName, PayTermsGrpCode, PriceListNum, SalesPersonCode, Cellular, EmailAddress, CurrentAccountBalance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        clientes_rows,
    )

    cur.executemany(
        """
        INSERT INTO vendedores
        (SalesEmployeeCode, SalesEmployeeName, Telephone, Mobile, Email)
        VALUES (?, ?, ?, ?, ?)
        """,
        vendedores_rows,
    )

    cur.executemany(
        """
        INSERT INTO facturas_abiertas
        (CardCode, CardName, DocTotal, NumAtCard, DocDate, PaidToDate, DocDueDate, DiasDesdeCreacion, Clasificacion, SaldoPendiente)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        facturas_rows,
    )

    conn.commit()
    conn.close()

    print("¡Datos cargados en la base de datos exitosamente!")
    return True

if __name__ == "__main__":
    run_load_db()