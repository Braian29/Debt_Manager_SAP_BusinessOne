# services.py
from flask import render_template
from xhtml2pdf import pisa
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from models import obtener_datos
from get_Data_SAP.Z_run_scripts import run_scripts
from config import Config


def get_data():
  db_path = Config.DATABASE_PATH
  return obtener_datos(db_path)

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
    fromaddr = Config.MAIL_USERNAME  # Tu correo electrónico
    password = Config.MAIL_PASSWORD      # Tu contraseña
    
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
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)  # Reemplaza con tu servidor SMTP
        server.starttls()
        server.login(fromaddr, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False

def generate_and_send_reports(vendedores, clientes_con_info, format_number):
    """Genera y envía reportes para cada vendedor."""
    cc_emails = ['maximiliano.bolado@super-clin.com.ar', 'cuentas@super-clin.com.ar', "braian.alonso@super-clin.com.ar", "horacio.rodriguezbarcelone@super-clin.com.ar"]

    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    for vendedor in vendedores:
        vendedor_code = vendedor.get('SalesEmployeeCode')
        vendedor_name = vendedor.get('SalesEmployeeName')
        vendedor_email = vendedor.get('Email') # Obtener email del vendedor
        
        # Filtra clientes para este vendedor
        clientes_filtrados = [c for c in clientes_con_info if c.get('vendedor_code') == vendedor_code]
        
        if clientes_filtrados:
            # Ordenar clientes por saldo vencido de mayor a menor
            clientes_filtrados = sorted(clientes_filtrados, key=lambda k: k['saldos_por_categoria'].get('Vencida', 0), reverse=True)

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
                    return f"Error al enviar correo del vendedor {vendedor_name}."
            else:
                return f"Error al generar reporte del vendedor {vendedor_name}."
            
    return "Reportes generados y enviados con éxito."

def update_data_service():
     if run_scripts():
          return "Datos actualizados correctamente!", "success"
     else:
        return "Error al actualizar los datos.", "error"