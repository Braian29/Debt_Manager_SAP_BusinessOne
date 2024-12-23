#routes.py
from flask import Flask, render_template
import sqlite3
import locale
from collections import defaultdict
from get_Data_SAP.Z_run_scripts import run_scripts
from xhtml2pdf import pisa
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

# Configuración similar a tu app.py
app = Flask(__name__)
locale.setlocale(locale.LC_ALL, 'es_AR.utf8')

# Resto del código de tu app.py
def format_number(value):
   if value is None:
      return ""
   try:
      return locale.format_string('%.2f', value, grouping=True)
   except ValueError:
      return str(value)

app.jinja_env.filters['format_number'] = format_number

def obtener_conexion():
    conn = sqlite3.connect('mi_base_datos.db')
    conn.row_factory = sqlite3.Row
    return conn

def obtener_datos():
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
    
    vendedores_map = {v['SalesEmployeeCode']: v for v in vendedores}

    facturas_por_cliente = defaultdict(list)
    for invoice in invoices:
        card_code = invoice.get('CardCode')
        try:
           invoice['PaidToDate'] = float(invoice.get('PaidToDate', 0))
        except (ValueError, TypeError):
          invoice['PaidToDate'] = 0
        facturas_por_cliente[card_code].append(invoice)
    clientes_con_info = []
    for cliente in clientes:
        vendedor_code = cliente.get('SalesPersonCode')
        vendedor = vendedores_map.get(vendedor_code)
        
        saldos_por_categoria = {
            'En Fecha': 0,
            'Proxima a Vencer': 0,
            'Vencida': 0
        }
         
        total_saldo = 0
        for factura in facturas_por_cliente.get(cliente.get('CardCode'), []):
            saldo_pendiente = factura.get('SaldoPendiente',0)
            clasificacion = factura.get('Clasificacion')
            total_saldo += saldo_pendiente
            if clasificacion in saldos_por_categoria:
               saldos_por_categoria[clasificacion] += saldo_pendiente

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

        
        
    # Agrupar información por vendedor
    vendedores_con_saldos = []
    for vendedor in vendedores:
        vendedor_code = vendedor.get('SalesEmployeeCode')
        
        saldos_por_categoria_vendedor = {
             'En Fecha': 0,
             'Proxima a Vencer': 0,
            'Vencida': 0
         }
        total_saldo_vendedor = 0
        clientes_del_vendedor = [c for c in clientes_con_info if c.get('vendedor_code') == vendedor_code]
        for cliente in clientes_del_vendedor:
              for categoria,saldo in cliente.get('saldos_por_categoria').items():
                  saldos_por_categoria_vendedor[categoria] += saldo
              total_saldo_vendedor += cliente.get('CurrentAccountBalance',0)
          
        saldo_vencido_vendedor = saldos_por_categoria_vendedor['Vencida']
        porcentaje_vencido_vendedor = (saldo_vencido_vendedor / total_saldo_vendedor) * 100 if total_saldo_vendedor else 0

        vendedor_info = {
           'SalesEmployeeCode': vendedor.get('SalesEmployeeCode'),
           'SalesEmployeeName': vendedor.get('SalesEmployeeName'),
           'saldos_por_categoria': saldos_por_categoria_vendedor,
           'total_saldo':total_saldo_vendedor,
           'porcentaje_vencido':porcentaje_vencido_vendedor
        }
        vendedores_con_saldos.append(vendedor_info)
    
    vendedores_con_saldos = [vendedor for vendedor in vendedores_con_saldos if vendedor['total_saldo'] > 0]


    return clientes_con_info, vendedores, vendedores_con_saldos
 
clientes_con_info, vendedores ,vendedores_con_saldos= obtener_datos()

@app.route('/')
def index():
    return render_template('index.html', clientes=clientes_con_info)

@app.route('/cliente/<string:card_code>')
def cliente_detail(card_code):
    global clientes_con_info
    cliente = next((c for c in clientes_con_info if c['CardCode'] == card_code), None)
    if cliente:
        return render_template('cliente_detail.html', cliente=cliente)
    else:
        return "Cliente no encontrado", 404

@app.route('/vendedores')
def vendedores_list():
    global vendedores
    return render_template('vendedores.html', vendedores=vendedores)

@app.route('/vendedores_con_saldos')
def vendedores_con_saldos_list():
    global vendedores_con_saldos
    return render_template('vendedores_con_saldos.html', vendedores=vendedores_con_saldos)
   
@app.route('/dashboard')
def dashboard():
    global clientes_con_info
    global vendedores_con_saldos
    total_deuda = sum(cliente.get('CurrentAccountBalance', 0) or 0 for cliente in clientes_con_info)

    saldos_por_categoria_clientes = {
      'En Fecha':0,
      'Proxima a Vencer':0,
      'Vencida':0,
    }
    for cliente in clientes_con_info:
       for categoria,saldo in cliente.get('saldos_por_categoria').items():
          saldos_por_categoria_clientes[categoria] += saldo

    labels_vendedores = [vendedor.get('SalesEmployeeName') for vendedor in vendedores_con_saldos]
    deudas_vendedores = [vendedor.get('total_saldo',0) for vendedor in vendedores_con_saldos]
  
    return render_template('dashboard.html', 
                           total_deuda=total_deuda, 
                           saldos_por_categoria_clientes=saldos_por_categoria_clientes,
                           labels_vendedores = labels_vendedores,
                           deudas_vendedores = deudas_vendedores
                           )


@app.route('/update_data', methods=['POST'])
def update_data():
    global clientes_con_info
    global vendedores
    global vendedores_con_saldos
    
    if run_scripts():
         clientes_con_info, vendedores , vendedores_con_saldos = obtener_datos()
         return render_template('update_result.html', message="Datos actualizados correctamente!", message_type="success")
    else:
        return render_template('update_result.html', message="Error al actualizar los datos.", message_type="error"), 500
    
    
# Funciones para Generar y Enviar Reportes
def generate_report_pdf(template_name, data, output_path):
    """Genera un PDF a partir de una plantilla HTML y datos."""
    rendered_html = render_template(template_name, **data)
    
    with open(output_path, "w+b") as pdf_file:
       pisa_status = pisa.CreatePDF(
           rendered_html,
           dest=pdf_file,
           encoding='utf-8'  
           )
    if pisa_status.err:
       return False
    return True
    


def send_email(subject, body, to_email, pdf_path, cc=None):
    """Envía un correo electrónico con un PDF adjunto."""
    fromaddr = "braian.alonso@super-clin.com.ar"  # Tu correo electrónico
    password = "alon3786"      # Tu contraseña
    
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = to_email
    msg['Subject'] = subject

    if cc:
      msg['Cc'] = ', '.join(cc)

    msg.attach(MIMEText(body, 'plain'))

    with open(pdf_path, "rb") as f:
        pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
    pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
    msg.attach(pdf_attachment)


    try:
        server = smtplib.SMTP('smtp.super-clin.com.ar', 587)  # Reemplaza con tu servidor SMTP
        server.starttls()
        server.login(fromaddr, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False




@app.route('/generate_reports', methods=['POST'])
def generate_reports():
    """Ruta para generar y enviar reportes por vendedor."""
    global vendedores
    global clientes_con_info

    # Lista de correos en copia (supervisores y jefes de venta)
    cc_emails = ["braianalonso29@gmail.com", "braianalonso29@gmail.com", "braianalonso29@gmail.com"]

    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    for vendedor in vendedores:
        vendedor_code = vendedor.get('SalesEmployeeCode')
        vendedor_name = vendedor.get('SalesEmployeeName')
        vendedor_email = vendedor.get('Email') # Obtener email del vendedor

        # Filtra clientes para este vendedor
        clientes_filtrados = [c for c in clientes_con_info if c.get('vendedor_code') == vendedor_code]
        
        if clientes_filtrados:
            report_data = {
                'vendedor_name': vendedor_name,
                'clientes': clientes_filtrados,
                'format_number': format_number #Pasamos el filtro
            }
            report_filename = f"{vendedor_code}_report.pdf"
            report_path = os.path.join(report_dir, report_filename)
            if generate_report_pdf('report_template.html', report_data, report_path):
                email_subject = f"Reporte de Clientes de {vendedor_name}"
                email_body = f"Adjunto encontrarás el reporte de clientes de {vendedor_name}."
                # Reemplazar con la dirección de correo del vendedor
                email_to = vendedor_email if vendedor_email else "superclinsys@gmail.com" #Usar el email del vendedor si existe, sino el default
                if not send_email(email_subject, email_body, email_to, report_path, cc=cc_emails): #Llamar a send_email con cc
                    return render_template('report_result.html', message=f"Error al enviar correo del vendedor {vendedor_name}.", message_type="error"), 500
            else:
                return render_template('report_result.html', message=f"Error al generar reporte del vendedor {vendedor_name}.", message_type="error"), 500

    return render_template('report_result.html', message="Reportes generados y enviados con éxito.", message_type="success")