from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


COL_WIDTHS = [230, 105, 105, 105, 105, 110]

C_TEXT = colors.HexColor("#0f172a")
C_MUTED = colors.HexColor("#64748b")
C_BORDER = colors.HexColor("#e2e8f0")
C_HEADER_BG = colors.HexColor("#eef2f7")
C_ZEBRA = colors.HexColor("#f8fafc")
C_GREEN = colors.HexColor("#15803d")
C_GREEN_BG = colors.HexColor("#dcfce7")
C_AMBER = colors.HexColor("#b45309")
C_AMBER_BG = colors.HexColor("#fef3c7")
C_RED = colors.HexColor("#b91c1c")
C_RED_BG = colors.HexColor("#fee2e2")
C_RED_DARK = colors.HexColor("#7f1d1d")


@dataclass(frozen=True)
class ReportData:
    vendedor_name: str
    generated_at: str
    clientes: list[dict]


def _money_or_dash(value, format_number) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    if v == 0:
        return "—"
    return f"$ {format_number(v)}"


def _fmt_date(d) -> str:
    if not d:
        return "—"
    try:
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(d)


def overdue_invoices(cliente: dict, today: date | None = None) -> list[tuple[dict, int]]:
    """Facturas con vencimiento < hoy y saldo pendiente, con días de atraso (más atrasadas primero)."""
    today = today or date.today()
    result = []
    for f in cliente.get("facturas") or []:
        due = f.get("_DocDueDate")
        if due is None or due >= today:
            continue
        if float(f.get("SaldoPendiente") or 0) <= 0:
            continue
        result.append((f, (today - due).days))
    result.sort(key=lambda t: t[1], reverse=True)
    return result


def _estado(cliente: dict, overdue: list[tuple[dict, int]]) -> tuple[str, colors.Color, colors.Color]:
    """(texto, color texto, color fondo) según facturas vencidas por fecha de vencimiento."""
    if not overdue:
        return "Al día", C_GREEN, C_GREEN_BG
    saldo_total = float(cliente.get("CurrentAccountBalance") or 0)
    saldo_vencido = sum(float(f.get("SaldoPendiente") or 0) for f, _ in overdue)
    pct = (saldo_vencido / saldo_total * 100) if saldo_total > 0 else 100.0
    pct = min(pct, 100.0)
    if pct <= 20:
        return f"Vencido {pct:.0f}%", C_AMBER, C_AMBER_BG
    return f"Vencido {pct:.0f}%", C_RED, C_RED_BG


def _days_color(days: int) -> colors.Color:
    if days <= 30:
        return C_AMBER
    if days <= 90:
        return C_RED
    return C_RED_DARK


def build_footer(canvas, doc, generated_at: str):
    """
    Footer con número de página. Se usa en onFirstPage/onLaterPages.
    """
    canvas.saveState()
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(C_MUTED)
    y = 10 * mm
    canvas.drawString(doc.leftMargin, y, "Sistema de Cobranzas")
    canvas.drawCentredString(doc.pagesize[0] / 2, y, generated_at)
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, y, f"Página {doc.page}")
    canvas.restoreState()


def build_cover_page(data: ReportData, format_number) -> list:
    """
    Portada (Página 1): título + vendedor + fecha + KPIs.
    """
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=C_TEXT,
        alignment=0,
        spaceAfter=10,
    )
    meta = ParagraphStyle(
        "CoverMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceAfter=14,
    )
    kpi_style = ParagraphStyle(
        "KPI",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=C_TEXT,
    )
    kpi_label = ParagraphStyle(
        "KPILabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=C_MUTED,
    )

    today = date.today()
    overdue_by_client = [overdue_invoices(c, today) for c in data.clientes]
    clientes_count = len(data.clientes)
    clientes_con_vencidas = sum(1 for o in overdue_by_client if o)
    max_dias = max((o[0][1] for o in overdue_by_client if o), default=0)
    saldo_total = sum(float(c.get("CurrentAccountBalance") or 0) for c in data.clientes)
    total_vencido = sum(float((c.get("saldos_por_categoria") or {}).get("Vencida") or 0) for c in data.clientes)

    story: list = []
    story.append(Spacer(1, 14 * mm))
    story.append(Paragraph("Cuentas Corrientes / Cobranzas", title))
    story.append(Paragraph(f"<b>Vendedor:</b> {data.vendedor_name}<br/><b>Generado:</b> {data.generated_at}", meta))

    kpi_rows = [
        [
            Paragraph("CLIENTES", kpi_label),
            Paragraph("CLIENTES CON VENCIDAS", kpi_label),
            Paragraph("SALDO TOTAL", kpi_label),
            Paragraph("TOTAL VENCIDO", kpi_label),
            Paragraph("FACTURA MÁS ATRASADA", kpi_label),
        ],
        [
            Paragraph(str(clientes_count), kpi_style),
            Paragraph(f"<font color='#b91c1c'>{clientes_con_vencidas}</font>", kpi_style),
            Paragraph(_money_or_dash(saldo_total, format_number), kpi_style),
            Paragraph(f"<font color='#b91c1c'>{_money_or_dash(total_vencido, format_number)}</font>", kpi_style),
            Paragraph(f"{max_dias} días" if max_dias else "—", kpi_style),
        ],
    ]
    kpi_table = Table(kpi_rows, colWidths=[130, 150, 170, 170, 140], hAlign="LEFT")
    kpi_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 6 * mm))
    return story


def build_summary(data: ReportData, format_number) -> list:
    """
    (Opcional) Resumen adicional como bloques. Lo mantenemos separado por arquitectura.
    Hoy la portada ya incluye KPIs; esta función queda para extensiones futuras.
    """
    return []


def _build_overdue_subtable(overdue: list[tuple[dict, int]], format_number) -> Table:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "OverdueTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=C_RED,
    )

    header = ["Documento", "Fecha doc.", "Vencimiento", "Días vencida", "Saldo"]
    rows: list[list] = [header]
    for f, dias in overdue:
        rows.append(
            [
                str(f.get("NumAtCard") or "—"),
                _fmt_date(f.get("_DocDate")),
                _fmt_date(f.get("_DocDueDate")),
                f"{dias} día" if dias == 1 else f"{dias} días",
                _money_or_dash(f.get("SaldoPendiente"), format_number),
            ]
        )

    sub = Table(rows, colWidths=[190, 95, 95, 95, 120], hAlign="LEFT", repeatRows=1)
    ts = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_MUTED),
            ("TEXTCOLOR", (0, 1), (-1, -1), C_TEXT),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, C_BORDER),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
    )
    for i, (_, dias) in enumerate(overdue, start=1):
        ts.add("TEXTCOLOR", (3, i), (3, i), _days_color(dias))
        if dias > 90:
            ts.add("FONTNAME", (3, i), (3, i), "Helvetica-Bold")
    sub.setStyle(ts)

    wrapper = Table(
        [[Paragraph(f"Facturas vencidas ({len(overdue)})", title_style)], [sub]],
        colWidths=[sum(COL_WIDTHS) - 40],
        hAlign="LEFT",
    )
    wrapper.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7f7")),
                ("LINEBEFORE", (0, 0), (0, -1), 2, C_RED),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return wrapper


def build_table(data: ReportData, format_number) -> list:
    styles = getSampleStyleSheet()
    client_style = ParagraphStyle(
        "ClientCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=C_TEXT,
    )

    header = ["CLIENTE", "SALDO TOTAL", "EN FECHA", "PRÓXIMO", "VENCIDO", "ESTADO"]
    rows: list[list] = [header]

    clientes_sorted = sorted(
        data.clientes,
        key=lambda c: float((c.get("saldos_por_categoria") or {}).get("Vencida") or 0),
        reverse=True,
    )

    today = date.today()
    total_saldo = 0.0
    total_vencido = 0.0

    # (índice de fila, colores de estado) para filas resumen; índices de filas de detalle
    summary_rows: list[tuple[int, colors.Color, colors.Color]] = []
    detail_rows: list[int] = []

    for c in clientes_sorted:
        name = c.get("CardName") or ""
        code = c.get("CardCode") or ""
        saldos = c.get("saldos_por_categoria") or {}
        saldo_total = c.get("CurrentAccountBalance") or 0
        vencido = saldos.get("Vencida") or 0
        overdue = overdue_invoices(c, today)
        estado_txt, estado_fg, estado_bg = _estado(c, overdue)

        try:
            total_saldo += float(saldo_total or 0)
        except (TypeError, ValueError):
            pass
        try:
            total_vencido += float(vencido or 0)
        except (TypeError, ValueError):
            pass

        summary_rows.append((len(rows), estado_fg, estado_bg))
        rows.append(
            [
                Paragraph(f"<b>{name}</b><br/><font color='#64748b' size='8'>{code}</font>", client_style),
                _money_or_dash(saldo_total, format_number),
                _money_or_dash(saldos.get("En Fecha"), format_number),
                _money_or_dash(saldos.get("Proxima a Vencer"), format_number),
                _money_or_dash(vencido, format_number),
                estado_txt,
            ]
        )

        if overdue:
            detail_rows.append(len(rows))
            rows.append([_build_overdue_subtable(overdue, format_number), "", "", "", "", ""])

    totals_idx = len(rows)
    rows.append(
        [
            Paragraph("<b>Totales</b>", client_style),
            _money_or_dash(total_saldo, format_number),
            "—",
            "—",
            _money_or_dash(total_vencido, format_number),
            "",
        ]
    )

    table = Table(rows, colWidths=COL_WIDTHS, repeatRows=1, hAlign="LEFT")

    ts = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_MUTED),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTNAME", (1, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (1, 1), (-1, -1), 9),
            ("TEXTCOLOR", (1, 1), (-1, -1), C_TEXT),
            ("ALIGN", (1, 0), (4, -1), "RIGHT"),
            ("ALIGN", (5, 0), (5, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, C_BORDER),
        ]
    )

    for i, (r, fg, bg) in enumerate(summary_rows):
        if i % 2 == 1:
            ts.add("BACKGROUND", (0, r), (4, r), C_ZEBRA)
        ts.add("LINEABOVE", (0, r), (-1, r), 0.25, C_BORDER)
        ts.add("TEXTCOLOR", (4, r), (4, r), C_RED)
        ts.add("FONTNAME", (4, r), (4, r), "Helvetica-Bold")
        ts.add("BACKGROUND", (5, r), (5, r), bg)
        ts.add("TEXTCOLOR", (5, r), (5, r), fg)
        ts.add("FONTNAME", (5, r), (5, r), "Helvetica-Bold")

    for r in detail_rows:
        ts.add("NOSPLIT", (0, r - 1), (-1, r))
        ts.add("SPAN", (0, r), (-1, r))
        ts.add("LEFTPADDING", (0, r), (-1, r), 30)
        ts.add("TOPPADDING", (0, r), (-1, r), 0)
        ts.add("BOTTOMPADDING", (0, r), (-1, r), 8)

    ts.add("LINEABOVE", (0, totals_idx), (-1, totals_idx), 0.75, C_BORDER)
    ts.add("BACKGROUND", (0, totals_idx), (-1, totals_idx), C_HEADER_BG)
    ts.add("FONTNAME", (1, totals_idx), (-1, totals_idx), "Helvetica-Bold")

    table.setStyle(ts)
    return [table]


def generate_pdf_report(output_path: str, data: ReportData, format_number):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Cuentas Corrientes / Cobranzas",
        author="Deuda_SAP",
    )

    story: list = []
    story.extend(build_cover_page(data, format_number))
    story.extend(build_summary(data, format_number))
    story.append(PageBreak())
    story.extend(build_table(data, format_number))

    def _footer(canvas, doc):
        return build_footer(canvas, doc, generated_at=data.generated_at)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
