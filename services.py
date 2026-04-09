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


def _build_mime_message(subject, body, to_email, pdf_path=None, cc=None):
    fromaddr = Config.MAIL_USERNAME
    msg = MIMEMultipart()
    msg["From"] = fromaddr
    msg["To"] = to_email
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.attach(MIMEText(body, "plain"))
    if pdf_path:
        from email.mime.application import MIMEApplication

        with open(pdf_path, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
        pdf_attachment.add_header(
            "Content-Disposition", "attachment", filename=os.path.basename(pdf_path)
        )
        msg.attach(pdf_attachment)
    return msg


def _smtp_open():
    s = smtplib.SMTP(Config.MAIL_SERVER, int(Config.MAIL_PORT))
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


def send_email(subject, body, to_email, pdf_path=None, cc=None, smtp=None):
    """Envía un correo electrónico. Adjunta PDF si `pdf_path` no es None.
    Si se pasa `smtp`, reutiliza la conexión y no la cierra."""
    msg = _build_mime_message(subject, body, to_email, pdf_path, cc)
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

        report_filename = f"{vendedor_code}_report.pdf"
        report_path = os.path.join(report_dir, report_filename)
        if not generate_report_pdf_reportlab(
            vendedor_name=vendedor_name,
            generated_at=generated_at,
            clientes=clientes_filtrados,
            output_path=report_path,
            format_number=format_number,
        ):
            return f"Error al generar reporte del vendedor {vendedor_name}."

        created += 1

    if created == 0:
        return "No se generaron reportes (no se encontraron clientes por vendedor)."
    return f"Reportes generados con éxito. Total: {created}."


def generate_and_send_reports(vendedores, clientes_con_info, format_number):
    """Genera y envía reportes para cada vendedor."""
    cc_emails = ['romina.galdos@super-clin.com.ar', 'cuentas@super-clin.com.ar', "braian.alonso@super-clin.com.ar", "horacio.rodriguezbarcelone@super-clin.com.ar"]

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

            report_filename = f"{vendedor_code}_report.pdf"
            report_path = os.path.join(report_dir, report_filename)
            if generate_report_pdf_reportlab(
                vendedor_name=vendedor_name,
                generated_at=generated_at,
                clientes=clientes_filtrados,
                output_path=report_path,
                format_number=format_number,
            ):
                email_subject = f"Reporte de Clientes de {vendedor_name}"
                email_body = f"Adjunto encontrarás el reporte de clientes de {vendedor_name}."
                # Reemplazar con la dirección de correo del vendedor
                email_to = vendedor_email if vendedor_email else "superclinsys@gmail.com" #Usar el email del vendedor si existe, sino el default
                if not send_email(email_subject, email_body, email_to, report_path, cc=cc_emails): #Llamar a send_email con cc
                    return f"Error al enviar correo del vendedor {vendedor_name}."
            else:
                return f"Error al generar reporte del vendedor {vendedor_name}."
            
    return "Reportes generados y enviados con éxito."


def _build_client_email(
    has_overdue: bool,
    cliente_nombre: str,
    saldo_total: float,
    saldo_vencido: float,
    generated_at: str,
    format_number,
):
    """
    Construye asunto y cuerpo según si existe al menos 1 documento vencido por DocDueDate < hoy.
    """
    saldo_total_txt = f"$ {format_number(saldo_total)}" if saldo_total else "—"
    saldo_vencido_txt = f"$ {format_number(saldo_vencido)}" if saldo_vencido else "—"

    if has_overdue:
        subject = "Estado de cuenta – Documentos vencidos"
        body = (
            f"Estimado/a {cliente_nombre},\n\n"
            f"Adjuntamos su estado de cuenta al {generated_at}.\n"
            f"Saldo total: {saldo_total_txt}\n"
            f"Total vencido: {saldo_vencido_txt}\n\n"
            "Si alguna facturas ya fue abonada, por favor ignore este correo.\n"
            "Ante cualquier consulta, puede responder a este correo.\n\n"
            "Saludos.\n"
        )
    else:
        subject = "Estado de cuenta – Próximos vencimientos"
        body = (
            f"Estimado/a {cliente_nombre},\n\n"
            f"Adjuntamos su estado de cuenta al {generated_at}.\n"
            f"Saldo total: {saldo_total_txt}\n"
            f"Total vencido: {saldo_vencido_txt}\n\n"
            "Recordatorio: revise los próximos vencimientos para evitar mora.\n"
            "Ante cualquier consulta, puede responder a este correo.\n\n"
            "Saludos.\n"
        )
    return subject, body


def _format_invoices_table(facturas: list[dict], format_number) -> tuple[str, float, float, float]:
    """
    Construye una tabla de texto monoespaciada para el cuerpo del mail.
    Retorna: (table_str, total_total, total_pagado, total_saldo)
    """
    today = datetime.now().date()

    def due_date(f: dict):
        return f.get("_DocDueDate")

    # Orden: vencidas primero (por due date), luego por saldo desc
    facturas_sorted = sorted(
        facturas,
        key=lambda f: (
            0 if (due_date(f) is not None and due_date(f) < today) else 1,
            -float(f.get("SaldoPendiente") or 0),
        ),
    )

    def money(v):
        try:
            x = float(v or 0)
        except (TypeError, ValueError):
            x = 0.0
        if x == 0:
            return "—"
        return f"$ {format_number(x)}"

    def fmt_due(d):
        if not d:
            return "—"
        try:
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(d)

    # Column widths for plain text table
    W_DOC = 18
    W_VTO = 10
    W_MONEY = 16

    header = (
        f"{'Doc':<{W_DOC}}"
        f"{'Vto':<{W_VTO}}"
        f"{'Total':>{W_MONEY}}"
        f"{'Pagado':>{W_MONEY}}"
        f"{'Saldo':>{W_MONEY}}"
    )
    lines = [header]

    total_total = 0.0
    total_pagado = 0.0
    total_saldo = 0.0

    for f in facturas_sorted:
        doc = str(f.get("NumAtCard") or "—")[:W_DOC]
        vto = fmt_due(due_date(f))[:W_VTO]
        total = float(f.get("DocTotal") or 0)
        pagado = float(f.get("PaidToDate") or 0)
        saldo = float(f.get("SaldoPendiente") or 0)

        total_total += total
        total_pagado += pagado
        total_saldo += saldo

        lines.append(
            f"{doc:<{W_DOC}}"
            f"{vto:<{W_VTO}}"
            f"{money(total):>{W_MONEY}}"
            f"{money(pagado):>{W_MONEY}}"
            f"{money(saldo):>{W_MONEY}}"
        )

    lines.append(
        f"{'Totales':<{W_DOC + W_VTO}}"
        f"{money(total_total):>{W_MONEY}}"
        f"{money(total_pagado):>{W_MONEY}}"
        f"{money(total_saldo):>{W_MONEY}}"
    )

    return "\n".join(lines), total_total, total_pagado, total_saldo


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
            facturas = c.get("facturas") or []

            # Criterio pedido basado en vencimiento real
            has_overdue = bool(c.get("has_overdue_due_date"))

            saldo_total = float(c.get("CurrentAccountBalance") or 0)
            # saldo vencido por due date (sumar saldo pendiente de facturas vencidas)
            saldo_vencido = _saldo_vencido_due_date(c)

            subject, body = _build_client_email(
                has_overdue=has_overdue,
                cliente_nombre=card_name,
                saldo_total=saldo_total,
                saldo_vencido=saldo_vencido,
                generated_at=generated_at,
                format_number=format_number,
            )

            # Desglose factura-a-factura dentro del correo
            table_txt, total_total, total_pagado, total_saldo = _format_invoices_table(facturas, format_number)
            body += (
                "\n"
                "El listado de Facturas abiertas son las siguientes:\n"
                f"{table_txt}\n\n"
            )

            if has_overdue:
                body += (
                    "Le solicitamos por favor regularizar los documentos vencidos y proximos a vencer a la brevedad.\n"
                )
            else:
                body += (
                    "Le solicitamos por favor tener en cuenta los próximos vencimientos para evitar mora.\n"
                )
            body += (
                "Ante cualquier consulta, puede responder a este correo.\n\n"
                "NOTA IMPORTANTE: LA información presente no cuenta con Notas de Crédito o Pagos no conciliados. La próxima semana recibirá la información completa.\n\n"
                "Saludos.\n"
            )

            if override_to:
                subject = f"[TEST CLIENTES] {subject} | {card_code} {card_name}"
                body = (
                    f"DESTINATARIO REAL: {email or 'SIN EMAIL'}\n"
                    f"CLIENTE: {card_code} - {card_name}\n\n"
                ) + body

            if smtp is None:
                smtp = _smtp_open()

            msg = _build_mime_message(subject, body, to_email, None, None)
            ok, smtp = _send_message_with_rate_limit_retries(smtp, msg)
            if not ok:
                errors += 1
                continue

            sent += 1
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