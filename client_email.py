from __future__ import annotations

from datetime import date
from html import escape

NOTA_IMPORTANTE = (
    "La información presente no incluye Notas de Crédito ni pagos no conciliados. "
    "La próxima semana recibirá la información completa."
)

C_TEXT = "#0f172a"
C_MUTED = "#64748b"
C_BORDER = "#e2e8f0"
C_HEADER_BG = "#f1f5f9"
C_RED = "#b91c1c"
C_RED_BG = "#fef2f2"
C_AMBER = "#b45309"
C_GREEN = "#15803d"

PROXIMO_DIAS = 7


def _fmt_date(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def _open_invoices(cliente: dict, today: date) -> list[dict]:
    """Facturas con saldo, ordenadas por vencimiento (las vencidas quedan primero)."""
    rows = []
    for f in cliente.get("facturas") or []:
        saldo = float(f.get("SaldoPendiente") or 0)
        if saldo <= 0:
            continue
        due = f.get("_DocDueDate")
        dias = (due - today).days if due else None
        if dias is None:
            estado, color = "—", C_MUTED
        elif dias < 0:
            estado, color = f"Vencida hace {-dias} día{'s' if dias != -1 else ''}", C_RED
        elif dias == 0:
            estado, color = "Vence hoy", C_AMBER
        elif dias <= PROXIMO_DIAS:
            estado, color = f"Vence en {dias} día{'s' if dias != 1 else ''}", C_AMBER
        else:
            estado, color = "En fecha", C_GREEN
        rows.append(
            {
                "doc": str(f.get("NumAtCard") or "—"),
                "fecha": f.get("_DocDate"),
                "vto": due,
                "total": float(f.get("DocTotal") or 0),
                "pagado": float(f.get("PaidToDate") or 0),
                "saldo": saldo,
                "vencida": dias is not None and dias < 0,
                "estado": estado,
                "color": color,
            }
        )
    rows.sort(key=lambda r: (r["vto"] is None, r["vto"] or date.max))
    return rows


def build_client_email(
    cliente: dict,
    generated_at: str,
    format_number,
    *,
    test_banner: str | None = None,
    today: date | None = None,
) -> tuple[str, str, str]:
    """Devuelve (asunto, texto plano, html) del estado de cuenta del cliente."""
    today = today or date.today()

    def money(v: float) -> str:
        return f"$ {format_number(v)}" if v else "—"

    nombre = cliente.get("CardName") or cliente.get("CardCode") or ""
    facturas = _open_invoices(cliente, today)
    saldo_total = float(cliente.get("CurrentAccountBalance") or 0)
    saldo_vencido = sum(f["saldo"] for f in facturas if f["vencida"])
    cant_vencidas = sum(1 for f in facturas if f["vencida"])
    show_pagado = any(f["pagado"] > 0 for f in facturas)

    if saldo_vencido > 0:
        subject = "Estado de cuenta – Documentos vencidos"
        pedido = "Le solicitamos regularizar a la brevedad los documentos vencidos."
    else:
        subject = "Estado de cuenta – Próximos vencimientos"
        pedido = "Le recordamos tener en cuenta los próximos vencimientos para evitar mora."
    cierre = (
        "Si alguna factura ya fue abonada, por favor desestime este aviso. "
        "Ante cualquier consulta, puede responder a este correo."
    )

    # ---------------------------------------------------------------- texto plano
    lines = []
    if test_banner:
        lines += [test_banner, ""]
    lines += [
        f"Estimado/a {nombre},",
        "",
        f"Le enviamos su estado de cuenta al {generated_at}.",
        "",
        f"Saldo total: {money(saldo_total)}",
        f"Total vencido: {money(saldo_vencido)}"
        + (f" ({cant_vencidas} factura{'s' if cant_vencidas != 1 else ''})" if cant_vencidas else ""),
        "",
        "Facturas abiertas:",
    ]
    for f in facturas:
        lines.append(
            f"- {f['doc']} | Fecha: {_fmt_date(f['fecha'])} | Vto: {_fmt_date(f['vto'])} | "
            f"Saldo: {money(f['saldo'])} | {f['estado']}"
        )
    lines += ["", pedido, cierre, "", f"Nota: {NOTA_IMPORTANTE}", "", "Saludos."]
    text = "\n".join(lines)

    # ---------------------------------------------------------------- html
    td = f"padding:8px 10px;border-bottom:1px solid {C_BORDER};"
    th = f"padding:8px 10px;background:{C_HEADER_BG};color:{C_MUTED};font-size:12px;text-transform:uppercase;"
    num = "text-align:right;white-space:nowrap;"

    headers = [("Documento", ""), ("Fecha doc.", ""), ("Vencimiento", "")]
    headers += [("Total", num)] + ([("Pagado", num)] if show_pagado else []) + [("Saldo", num), ("Estado", "")]
    head_html = "".join(f'<th style="{th}{extra}text-align:{"right" if extra else "left"};">{h}</th>' for h, extra in headers)

    body_rows = []
    for f in facturas:
        bg = f"background:{C_RED_BG};" if f["vencida"] else ""
        cells = [
            f'<td style="{td}{bg}white-space:nowrap;">{escape(f["doc"])}</td>',
            f'<td style="{td}{bg}white-space:nowrap;">{_fmt_date(f["fecha"])}</td>',
            f'<td style="{td}{bg}white-space:nowrap;">{_fmt_date(f["vto"])}</td>',
            f'<td style="{td}{bg}{num}">{money(f["total"])}</td>',
        ]
        if show_pagado:
            cells.append(f'<td style="{td}{bg}{num}">{money(f["pagado"])}</td>')
        cells += [
            f'<td style="{td}{bg}{num}font-weight:bold;">{money(f["saldo"])}</td>',
            f'<td style="{td}{bg}color:{f["color"]};font-weight:bold;white-space:nowrap;">{f["estado"]}</td>',
        ]
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    total_amounts = [sum(f["total"] for f in facturas)]
    if show_pagado:
        total_amounts.append(sum(f["pagado"] for f in facturas))
    total_amounts.append(sum(f["saldo"] for f in facturas))
    total_cells = (
        f'<td colspan="3" style="{td}font-weight:bold;">Total</td>'
        + "".join(f'<td style="{td}{num}font-weight:bold;">{money(v)}</td>' for v in total_amounts)
        + f'<td style="{td}"></td>'
    )

    banner_html = (
        f'<div style="padding:8px 12px;margin-bottom:16px;background:#fef9c3;border:1px solid #fde047;'
        f'font-size:12px;color:#713f12;">{escape(test_banner).replace(chr(10), "<br>")}</div>'
        if test_banner
        else ""
    )
    vencido_txt = money(saldo_vencido) + (
        f' <span style="font-size:12px;color:{C_MUTED};font-weight:normal;">({cant_vencidas} factura{"s" if cant_vencidas != 1 else ""})</span>'
        if cant_vencidas
        else ""
    )

    html = f"""\
<html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;">
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:{C_TEXT};max-width:820px;padding:16px;">
{banner_html}
<p style="margin:0 0 12px;">Estimado/a <b>{escape(nombre)}</b>,</p>
<p style="margin:0 0 16px;">Le enviamos su estado de cuenta al {escape(generated_at)}.</p>

<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;margin-bottom:20px;">
<tr>
<td style="padding:10px 16px;border:1px solid {C_BORDER};">
<div style="font-size:12px;color:{C_MUTED};text-transform:uppercase;">Saldo total</div>
<div style="font-size:18px;font-weight:bold;">{money(saldo_total)}</div>
</td>
<td style="padding:10px 16px;border:1px solid {C_BORDER};">
<div style="font-size:12px;color:{C_MUTED};text-transform:uppercase;">Total vencido</div>
<div style="font-size:18px;font-weight:bold;color:{C_RED if saldo_vencido else C_TEXT};">{vencido_txt}</div>
</td>
</tr>
</table>

<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;width:100%;font-size:13px;border:1px solid {C_BORDER};">
<tr>{head_html}</tr>
{''.join(body_rows)}
<tr style="background:{C_HEADER_BG};">{total_cells}</tr>
</table>

<p style="margin:20px 0 4px;">{pedido}</p>
<p style="margin:0 0 16px;">{cierre}</p>
<p style="margin:0 0 16px;font-size:12px;color:{C_MUTED};"><b>Nota:</b> {NOTA_IMPORTANTE}</p>
<p style="margin:0;">Saludos.</p>
</div>
</body></html>"""

    return subject, text, html
