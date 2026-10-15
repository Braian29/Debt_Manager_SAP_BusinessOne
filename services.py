from __future__ import annotations

import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from datetime import datetime
from models import obtener_datos
from get_Data_SAP.Z_run_scripts import run_scripts
from config import Config
from get_Data_SAP.sesion import get_new_session

from client_email import build_client_email
from excel_report import generate_excel_report, generate_manager_excel
from reportlab_report import ReportData, generate_pdf_report

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)+$"
)
_EMAIL_LOCAL_BLOCKLIST = frozenset(
    {
        "no",
        "sin",
        "n/a",
        "na",
        "null",
        "none",
        "-",
        "xxx",
        "s/n",
    }
)


def is_valid_client_email(addr: str | None) -> bool:
    """True si parece un email RFC razonable; rechaza valores típicos erróneos en SAP."""
    if not addr or not isinstance(addr, str):
        return False
    s = addr.strip()
    if len(s) < 6 or "@" not in s or " " in s:
        return False
    local, _, domain = s.partition("@")
    if not local or not domain or "." not in domain:
        return False
    if local.lower() in _EMAIL_LOCAL_BLOCKLIST:
        return False
    return _EMAIL_RE.match(s) is not None


_ATTACHMENT_SUBTYPES = {
    ".pdf": "pdf",
    ".xlsx": "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _build_mime_message(subject, body, to_email, attachment_path=None, cc=None, html=None):
    fromaddr = Config.MAIL_USERNAME
    msg = MIMEMultipart()
    msg["From"] = fromaddr
    msg["To"] = to_email
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = ", ".join(cc)
    if html:
        alternative = MIMEMultipart("alternative")
        alternative.attach(MIMEText(body, "plain", "utf-8"))
        alternative.attach(MIMEText(html, "html", "utf-8"))
        msg.attach(alternative)
    else:
        msg.attach(MIMEText(body, "plain"))
    if attachment_path:
        from email.mime.application import MIMEApplication

        ext = os.path.splitext(attachment_path)[1].lower()
        with open(attachment_path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype=_ATTACHMENT_SUBTYPES.get(ext, "octet-stream"))
        attachment.add_header(
            "Content-Disposition", "attachment", filename=os.path.basename(attachment_path)
        )
        msg.attach(attachment)
    return msg


def _smtp_open():
    # timeout evita que quede colgado “en silencio” ante red/SMTP lento
    s = smtplib.SMTP(Config.MAIL_SERVER, int(Config.MAIL_PORT), timeout=40)
    s.starttls()
    s.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
    return s


def _is_smtp_rate_limit_error(exc: BaseException) -> bool:
    if getattr(exc, "smtp_code", None) == 450:
        return True
    t = str(exc).lower()
    return "450" in t or "too much mail" in t


def _send_message_with_rate_limit_retries(smtp, msg) -> tuple[bool, object]:
    """Reintenta ante 450 (rate limit) con espera y nueva conexión."""
    backoff = 55
    for attempt in range(5):
        try:
            smtp.send_message(msg)
            return True, smtp
        except Exception as e:
            if _is_smtp_rate_limit_error(e) and attempt < 4:
                print(f"Límite SMTP (450), esperando {backoff}s antes de reintentar...")
                time.sleep(backoff)
                backoff = min(backoff + 35, 200)
                try:
                    smtp.quit()
                except Exception:
                    pass
                smtp = _smtp_open()
                continue
            print(f"Error al enviar correo: {e}")
            return False, smtp
    return False, smtp


def get_data():
  db_path = Config.DATABASE_PATH
  return obtener_datos(db_path)


def generate_report_pdf_reportlab(vendedor_name: str, generated_at: str, clientes: list[dict], output_path: str, format_number) -> bool:
    """
    Genera el PDF con ReportLab/Platypus (sin HTML).
    """
    try:
        data = ReportData(vendedor_name=vendedor_name, generated_at=generated_at, clientes=clientes)
        generate_pdf_report(output_path=output_path, data=data, format_number=format_number)
        return True
    except Exception as exc:
        print(f"Error al generar PDF (ReportLab): {exc}")
        return False


def generate_report_excel(vendedor_name: str, generated_at: str, clientes: list[dict], output_path: str) -> bool:
    try:
        generate_excel_report(output_path=output_path, vendedor_name=vendedor_name, generated_at=generated_at, clientes=clientes)
        return True
    except Exception as exc:
        print(f"Error al generar Excel: {exc}")
        return False


def send_email(subject, body, to_email, attachment_path=None, cc=None, smtp=None):
    """Envía un correo electrónico. Adjunta el archivo si `attachment_path` no es None (PDF o Excel).
    Si se pasa `smtp`, reutiliza la conexión y no la cierra."""
    msg = _build_mime_message(subject, body, to_email, attachment_path, cc)
    own = smtp is None
    if smtp is None:
        smtp = _smtp_open()
    try:
        smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False
    finally:
        if own:
            try:
                smtp.quit()
            except Exception:
                pass

def generate_reports_only(vendedores, clientes_con_info, format_number):
    """
    Genera reportes PDF por vendedor sin enviar correos.

    Retorna un string de estado (compatible con el estilo existente).
    """
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    created = 0
    for vendedor in vendedores:
        vendedor_code = vendedor.get("SalesEmployeeCode")
        vendedor_name = vendedor.get("SalesEmployeeName")

        clientes_filtrados = [c for c in clientes_con_info if c.get("vendedor_code") == vendedor_code]
        if not clientes_filtrados:
            continue

        clientes_filtrados = sorted(
            clientes_filtrados,
            key=lambda k: k["saldos_por_categoria"].get("Vencida", 0),
            reverse=True,
        )

        report_filename = f"{vendedor_code}_reporte_{datetime.now():%Y-%m-%d}.xlsx"
        report_path = os.path.join(report_dir, report_filename)
        if not generate_report_excel(
            vendedor_name=vendedor_name,
            generated_at=generated_at,
            clientes=clientes_filtrados,
            output_path=report_path,
        ):
            return f"Error al generar reporte del vendedor {vendedor_name}."

        created += 1

    if created == 0:
        return "No se generaron reportes (no se encontraron clientes por vendedor)."
    return f"Reportes generados con éxito. Total: {created}."


def generate_and_send_reports(vendedores, clientes_con_info, format_number):
    """Genera y envía reportes para cada vendedor."""
    cc_emails = ['romina.galdos@super-clin.com.ar', 
                 'cuentas@super-clin.com.ar', 
                 "braian.alonso@super-clin.com.ar", 
                 "carolina.kundler@super-clin.com.ar",
                 "miguel.molachino@super-clin.com.ar",
                     ]
                     # "horacio.rodriguezbarcelone@super-clin.com.ar", 

    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    for vendedor in vendedores:
        vendedor_code = vendedor.get('SalesEmployeeCode')
        vendedor_name = vendedor.get('SalesEmployeeName')
        vendedor_email = vendedor.get('Email') # Obtener email del vendedor
        
        # Filtra clientes para este vendedor
        clientes_filtrados = [c for c in clientes_con_info if c.get('vendedor_code') == vendedor_code]
        
        if clientes_filtrados:
            # Ordenar clientes por saldo vencido de mayor a menor
            clientes_filtrados = sorted(clientes_filtrados, key=lambda k: k['saldos_por_categoria'].get('Vencida', 0), reverse=True)

            report_filename = f"{vendedor_code}_reporte_{datetime.now():%Y-%m-%d}.xlsx"
            report_path = os.path.join(report_dir, report_filename)
            if generate_report_excel(
                vendedor_name=vendedor_name,
                generated_at=generated_at,
                clientes=clientes_filtrados,
                output_path=report_path,
            ):
                email_subject = f"Reporte de Clientes de {vendedor_name}"
                email_body = (
                    f"Adjunto encontrarás el reporte de clientes de {vendedor_name}.\n\n"
                    "Hoja 'Urgente': facturas con más de 60 días desde la venta y, después, las de 31 a 60 días.\n"
                    "Hoja 'Reporte completo': todas las facturas abiertas, con filtros por columna."
                )
                # Reemplazar con la dirección de correo del vendedor
                email_to = vendedor_email if vendedor_email else "superclinsys@gmail.com" #Usar el email del vendedor si existe, sino el default
                if not send_email(email_subject, email_body, email_to, report_path, cc=cc_emails): #Llamar a send_email con cc
                    return f"Error al enviar correo del vendedor {vendedor_name}."
            else:
                return f"Error al generar reporte del vendedor {vendedor_name}."
            
    return "Reportes generados y enviados con éxito."


MANAGER_EMAILS = [
    "rodolfo.bouabdo@super-clin.com.ar",
    "cuentas@super-clin.com.ar",
    "carolina.kundler@super-clin.com.ar",
    "braian.alonso@super-clin.com.ar",
]


def generate_manager_report(clientes_con_info) -> str | None:
    """Genera el Excel de gerentes en reports/. Devuelve la ruta o None si falla."""
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"gerentes_reporte_{datetime.now():%Y-%m-%d}.xlsx")
    try:
        generate_manager_excel(
            output_path=report_path,
            generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
            clientes=clientes_con_info,
        )
        return report_path
    except Exception as exc:
        print(f"Error al generar Excel de gerentes: {exc}")
        return None


def generate_and_send_manager_report(clientes_con_info, *, override_to: str | None = None) -> str:
    """Genera el Excel de gerentes y lo envía a MANAGER_EMAILS (o solo a `override_to` para pruebas)."""
    report_path = generate_manager_report(clientes_con_info)
    if not report_path:
        return "Error al generar el reporte de gerentes."

    subject = f"Status de Deuda al {datetime.now():%d-%m-%y}"
    body = (
        "Adjunto el status de deuda de clientes, clasificado por días desde la venta "
        "(0-30, 31-60, 61-90 y 91+).\n\n"
        "Hoja 'Resumen': totales por vendedor y tramo.\n"
        "Hoja 'Por cliente': deuda de cada cliente por tramo.\n"
        "Hoja 'Detalle': todas las facturas abiertas, con filtros por columna.\n"
    )
    if override_to:
        to_email, cc = override_to, None
        subject = f"[TEST GERENTES] {subject}"
    else:
        to_email, cc = MANAGER_EMAILS[0], MANAGER_EMAILS[1:]

    if not send_email(subject, body, to_email, report_path, cc=cc):
        return "Error al enviar el reporte de gerentes."
    return "Reporte de gerentes enviado con éxito."


def generate_and_send_client_reports(clientes_con_info, format_number, *, limit: int | None = None, override_to: str | None = None):
    """
    Envía 1 mail por cliente con desglose factura-a-factura en el cuerpo.
    El mensaje cambia si existe al menos 1 factura con DocDueDate < hoy.
    """
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    sent = 0
    skipped_no_email = 0
    errors = 0

    # Ordenar para pruebas: mayor vencido (por DocDueDate) primero
    def _saldo_vencido_due_date(cliente: dict) -> float:
        facturas = cliente.get("facturas") or []
        today = datetime.now().date()
        return sum(
            float(f.get("SaldoPendiente") or 0)
            for f in facturas
            if (f.get("_DocDueDate") is not None) and (f.get("_DocDueDate") < today)
        )

    clientes_sorted = sorted(
        clientes_con_info,
        key=lambda c: (_saldo_vencido_due_date(c), float(c.get("CurrentAccountBalance") or 0)),
        reverse=True,
    )

    if limit is not None:
        clientes_sorted = clientes_sorted[: max(0, int(limit))]

    if override_to is not None and not is_valid_client_email(override_to):
        return f"Error: override_to no es un email válido: {override_to!r}."

    mail_delay = float(getattr(Config, "MAIL_DELAY_SECONDS", 2.5))
    skipped_invalid_email = 0
    smtp = None

    try:
        for c in clientes_sorted:
            email = c.get("EmailAddress")
            if not override_to:
                if not email:
                    skipped_no_email += 1
                    continue
                if not is_valid_client_email(email):
                    skipped_invalid_email += 1
                    continue
            elif not email:
                pass

            to_email = override_to or email

            card_code = c.get("CardCode")
            card_name = c.get("CardName") or card_code

            test_banner = None
            if override_to:
                test_banner = f"PRUEBA - Destinatario real: {email or 'SIN EMAIL'}\nCliente: {card_code} - {card_name}"

            subject, body, html = build_client_email(c, generated_at, format_number, test_banner=test_banner)
            if override_to:
                subject = f"[TEST CLIENTES] {subject} | {card_code} {card_name}"

            if smtp is None:
                smtp = _smtp_open()

            msg = _build_mime_message(subject, body, to_email, None, None, html=html)
            ok, smtp = _send_message_with_rate_limit_retries(smtp, msg)
            if not ok:
                errors += 1
                continue

            sent += 1
            if sent == 1 or (sent % 10) == 0:
                print(
                    f"Progreso clientes: enviados={sent}, sin_email={skipped_no_email}, "
                    f"email_invalido={skipped_invalid_email}, errores={errors}"
                )
            time.sleep(mail_delay)
    finally:
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:
                pass

    tail = (
        f"enviados={sent}, sin_email={skipped_no_email}, "
        f"email_invalido={skipped_invalid_email}, errores={errors}"
    )
    if errors:
        return f"Error: {tail}."
    return f"Envíos a clientes completados. {tail}."

def update_data() -> bool:
    """
    Actualiza datos (SAP → JSON → SQLite).
    Mantiene el retry + refresh de sesión pero sin retornar respuestas "web".
    """
    max_retries = 2  # Max retries including the first attempt
    for attempt in range(max_retries):
        try:
            if run_scripts():
                return True

            if attempt < max_retries - 1:
                print("Error al actualizar los datos, intentando refrescar la sesión...")
                if get_new_session():
                    print("Sesión refrescada con éxito.")
                    continue
                print("Fallo al refrescar la sesión")
                return False

            return False
        except Exception as e:
            print(f"Error inesperado al actualizar los datos: {e}")
            if attempt < max_retries - 1 and get_new_session():
                continue
            return False