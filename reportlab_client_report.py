from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
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


@dataclass(frozen=True)
class ClientReportData:
    card_code: str
    card_name: str
    email: str | None
    generated_at: str
    facturas: list[dict]
    vendedor_name: str | None = None


def _parse_date(d):
    if not d:
        return None
    s = str(d)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None


def _money_or_dash(value, format_number) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    if v == 0:
        return "—"
    return f"$ {format_number(v)}"


def build_footer(canvas, doc, generated_at: str):
    canvas.saveState()
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    y = 10 * mm
    canvas.drawString(doc.leftMargin, y, "Sistema de Cobranzas")
    canvas.drawCentredString(doc.pagesize[0] / 2, y, generated_at)
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, y, f"Página {doc.page}")
    canvas.restoreState()


def build_cover_page(data: ClientReportData, format_number) -> list:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=8,
    )
    meta = ParagraphStyle(
        "CoverMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#374151"),
        spaceAfter=12,
    )

    today = date.today()
    # Totales (saldo pendiente)
    total_saldo = sum(float(f.get("SaldoPendiente") or 0) for f in data.facturas)
    total_vencido = sum(
        float(f.get("SaldoPendiente") or 0)
        for f in data.facturas
        if (f.get("_DocDueDate") or _parse_date(f.get("DocDueDate"))) and (f.get("_DocDueDate") or _parse_date(f.get("DocDueDate"))) < today
    )

    story: list = []
    story.append(Spacer(1, 14 * mm))
    story.append(Paragraph("Estado de Cuenta / Cobranzas", title))
    story.append(Paragraph(f"<b>Cliente:</b> {data.card_name}<br/><b>Código:</b> {data.card_code}", meta))
    if data.vendedor_name:
        story.append(Paragraph(f"<b>Vendedor:</b> {data.vendedor_name}", meta))
    story.append(Paragraph(f"<b>Generado:</b> {data.generated_at}", meta))

    kpi_label = ParagraphStyle(
        "KPILabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6b7280"),
    )
    kpi_val = ParagraphStyle(
        "KPIVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
    )

    kpis = Table(
        [
            [Paragraph("Saldo total", kpi_label), Paragraph("Total vencido", kpi_label)],
            [Paragraph(_money_or_dash(total_saldo, format_number), kpi_val), Paragraph(f"<font color='#b91c1c'>{_money_or_dash(total_vencido, format_number)}</font>", kpi_val)],
        ],
        colWidths=[85 * mm, 85 * mm],
    )
    kpis.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#e5e7eb")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(kpis)
    return story


def build_table(data: ClientReportData, format_number) -> list:
    today = date.today()
    styles = getSampleStyleSheet()

    # Column widths in points (portrait A4)
    # Eliminamos "Referencia" para evitar duplicación y ganar espacio.
    col_widths = [140, 80, 90, 90, 90]  # Doc / Vto / Total / Pagado / Saldo
    header = ["Doc", "Vto", "Total", "Pagado", "Saldo"]
    rows: list[list] = [header]

    facturas_sorted = sorted(
        data.facturas,
        key=lambda f: (
            0
            if ((f.get("_DocDueDate") or _parse_date(f.get("DocDueDate"))) and (f.get("_DocDueDate") or _parse_date(f.get("DocDueDate"))) < today)
            else 1,
            -float(f.get("SaldoPendiente") or 0),
        ),
    )

    total_total = 0.0
    total_pagado = 0.0
    total_saldo = 0.0

    for f in facturas_sorted:
        doc = f.get("NumAtCard") or ""
        due = f.get("_DocDueDate") or _parse_date(f.get("DocDueDate"))
        due_str = due.strftime("%d/%m/%Y") if due else "—"
        total = float(f.get("DocTotal") or 0)
        pagado = float(f.get("PaidToDate") or 0)
        saldo = float(f.get("SaldoPendiente") or 0)

        total_total += total
        total_pagado += pagado
        total_saldo += saldo

        rows.append(
            [
                str(doc),
                due_str,
                _money_or_dash(total, format_number),
                _money_or_dash(pagado, format_number),
                _money_or_dash(saldo, format_number),
            ]
        )

    rows.append(
        [
            "",
            Paragraph("<b>Totales</b>", styles["Normal"]),
            _money_or_dash(total_total, format_number),
            _money_or_dash(total_pagado, format_number),
            _money_or_dash(total_saldo, format_number),
        ]
    )

    table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    ts = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#6b7280")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#e5e7eb")),
            ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#eef2f7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )

    # numeric columns right + monospace
    ts.add("ALIGN", (2, 1), (4, -1), "RIGHT")
    ts.add("FONTNAME", (2, 1), (4, -1), "Courier")
    ts.add("FONTSIZE", (2, 1), (4, -1), 8.5)

    # zebra rows
    last = len(rows) - 1
    for r in range(1, last):
        if r % 2 == 0:
            ts.add("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f8fafc"))

        due = data.facturas[r - 1].get("_DocDueDate") or _parse_date(data.facturas[r - 1].get("DocDueDate"))
        if due and due < today:
            ts.add("TEXTCOLOR", (1, r), (1, r), colors.HexColor("#b91c1c"))
            ts.add("TEXTCOLOR", (4, r), (4, r), colors.HexColor("#991b1b"))

    # totals row
    ts.add("LINEABOVE", (0, last), (-1, last), 0.75, colors.HexColor("#e5e7eb"))
    ts.add("BACKGROUND", (0, last), (-1, last), colors.HexColor("#f3f4f6"))
    ts.add("FONTNAME", (0, last), (-1, last), "Helvetica-Bold")
    ts.add("ALIGN", (2, last), (4, last), "RIGHT")
    ts.add("FONTNAME", (2, last), (4, last), "Courier-Bold")

    table.setStyle(ts)
    return [table]


def generate_client_pdf(output_path: str, data: ClientReportData, format_number):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Estado de Cuenta / Cobranzas",
        author="Deuda_SAP",
    )

    story: list = []
    story.extend(build_cover_page(data, format_number))
    story.append(PageBreak())
    story.extend(build_table(data, format_number))

    def _footer(canvas, doc):
        return build_footer(canvas, doc, generated_at=data.generated_at)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

