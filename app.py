# app.py
import sqlite3
from flask import Flask, render_template
import locale
from collections import defaultdict
from get_Data_SAP.Z_run_scripts import run_scripts

app = Flask(__name__)

# Configurar la locale para formatos numéricos (puedes cambiar 'es_AR' a tu locale)
locale.setlocale(locale.LC_ALL, 'es_AR.utf8') 

def format_number(value):
    """Formatea un número usando la locale actual."""
    if value is None:
        return ""
    try:
        return locale.format_string('%.2f', value, grouping=True)
    except ValueError:
        return str(value) # Retornar como string si no puede formatear como número.

# Registrar el filtro en la aplicación
app.jinja_env.filters['format_number'] = format_number

def obtener_conexion():
    """Obtiene una conexión a la base de datos SQLite."""
    conn = sqlite3.connect('mi_base_datos.db')
    conn.row_factory = sqlite3.Row  # Para acceder a los resultados como diccionarios
    return conn

def obtener_datos():
    """Obtiene datos de la base de datos y los procesa."""
    conn = obtener_conexion()
    cursor = conn.cursor()

    # Obtener clientes
    cursor.execute("SELECT * FROM clientes_con_deuda")
    clientes = [dict(row) for row in cursor.fetchall()]
    
    # Obtener vendedores
    cursor.execute("SELECT * FROM vendedores")
    vendedores = [dict(row) for row in cursor.fetchall()]

    # Obtener facturas
    cursor.execute("SELECT * FROM facturas_abiertas")
    invoices = [dict(row) for row in cursor.fetchall()]
    
    conn.close()

    # Procesar datos
    # Crear diccionario para mapear vendedores por código
    vendedores_map = {v['SalesEmployeeCode']: v for v in vendedores}
    
    # Mapear facturas por CardCode
    facturas_por_cliente = defaultdict(list)
    for invoice in invoices:
        card_code = invoice.get('CardCode')
        # Convertir PaidToDate a float, usando un try/except en caso de que no se pueda convertir
        try:
           invoice['PaidToDate'] = float(invoice.get('PaidToDate', 0))
        except (ValueError, TypeError):
          invoice['PaidToDate'] = 0
        facturas_por_cliente[card_code].append(invoice)

    # Enriquecer clientes con vendedor y facturas
    clientes_con_info = []
    for cliente in clientes:
        vendedor_code = cliente.get('SalesPersonCode')
        vendedor = vendedores_map.get(vendedor_code)
        
        # Inicializar saldos por categoría
        saldos_por_categoria = {
            'En Fecha': 0,
            'Proxima a Vencer': 0,
            'Vencida': 0
        }
         # Calcular saldos por categoría
        total_saldo = 0
        for factura in facturas_por_cliente.get(cliente.get('CardCode'), []):
            saldo_pendiente = factura.get('SaldoPendiente',0) #Saldo Pendiente de la factura
            clasificacion = factura.get('Clasificacion')
            total_saldo += saldo_pendiente
            if clasificacion in saldos_por_categoria:
               saldos_por_categoria[clasificacion] += saldo_pendiente


        # Calcular porcentaje de vencidos
        saldo_vencido = saldos_por_categoria['Vencida']
        porcentaje_vencido = (saldo_vencido / total_saldo) * 100 if total_saldo else 0

        cliente_info = {
            'CardCode': cliente.get('CardCode'),
            'CardName': cliente.get('CardName'),
            'CurrentAccountBalance': cliente.get('CurrentAccountBalance'),
            'vendedor': vendedor.get('SalesEmployeeName') if vendedor else "Sin Vendedor Asignado",
            'vendedor_code': vendedor_code if vendedor else None,
             'facturas': facturas_por_cliente.get(cliente.get('CardCode'), []),
            'saldos_por_categoria': saldos_por_categoria,
            'porcentaje_vencido': porcentaje_vencido
        }
        clientes_con_info.append(cliente_info)
        
    return clientes_con_info, vendedores


clientes_con_info, vendedores = obtener_datos()


@app.route('/')
def index():
    return render_template('index.html', clientes=clientes_con_info)

@app.route('/cliente/<string:card_code>')
def cliente_detail(card_code):
    global clientes_con_info #Indicamos que usaremos la variable global
    cliente = next((c for c in clientes_con_info if c['CardCode'] == card_code), None)
    if cliente:
        return render_template('cliente_detail.html', cliente=cliente)
    else:
        return "Cliente no encontrado", 404

@app.route('/vendedores')
def vendedores_list():
    global vendedores  #Indicamos que usaremos la variable global
    return render_template('vendedores.html', vendedores=vendedores)

@app.route('/dashboard')
def dashboard():
    global clientes_con_info  #Indicamos que usaremos la variable global
    total_deuda = sum(cliente.get('CurrentAccountBalance', 0) or 0 for cliente in clientes_con_info)
    return render_template('dashboard.html', total_deuda=total_deuda, clientes=clientes_con_info)


@app.route('/update_data', methods=['POST'])
def update_data():
    global clientes_con_info #Indicamos que usaremos la variable global
    global vendedores   #Indicamos que usaremos la variable global
    
    if run_scripts():
         clientes_con_info, vendedores = obtener_datos()
         return "Datos actualizados correctamente!", 200
    else:
        return "Error al actualizar los datos.", 500

if __name__ == '__main__':
    app.run(debug=True)