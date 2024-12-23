from flask import render_template
from xhtml2pdf import pisa
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

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


def send_email(subject, body, to_email, pdf_path):
    """Envía un correo electrónico con un PDF adjunto."""
    fromaddr = "braian.alonso@super-clin.com.ar"  # Tu correo electrónico
    password = "alon3786"      # Tu contraseña
    
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = to_email
    msg['Subject'] = subject

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

def generate_and_send_reports(vendedores, clientes_con_info, format_number):
   
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    for vendedor in vendedores:
        vendedor_code = vendedor.get('SalesEmployeeCode')
        vendedor_name = vendedor.get('SalesEmployeeName')
        
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
                email_to = "superclinsys@gmail.com"
                if not send_email(email_subject, email_body, email_to, report_path):
                    return f"Error al enviar correo del vendedor {vendedor_name}."

            else:
                  return f"Error al generar reporte del vendedor {vendedor_name}."
    
    return "Reportes generados y enviados con éxito."