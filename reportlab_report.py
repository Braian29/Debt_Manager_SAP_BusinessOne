from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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


def _estado_label(mora_pct: float) -> str:
    if mora_pct >= 50:
        return "Vencido"
    if mora_pct >= 20:
        return "Atención"
    return "Al día"


def build_footer(canvas, doc, generated_at: str):
    """
    Footer con número de página. Se usa en onFirstPage/onLaterPages.
    """
    canvas.saveState()
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    page_text = f"Página {doc.page}"
    left_text = "Sistema de Cobranzas"
    mid_text = generated_at
    # izquierda | centro | derecha
    y = 10 * mm
    canvas.drawString(doc.leftMargin, y, left_text)
    canvas.drawCentredString(doc.pagesize[0] / 2, y, mid_text)
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, y, page_text)
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
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )
    meta = ParagraphStyle(
        "CoverMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#374151"),
        spaceAfter=14,
    )

    clientes_count = len(data.clientes)
    saldo_total = sum((c.get("CurrentAccountBalance") or 0) for c in data.clientes)
    total_vencido = sum((c.get("saldos_por_categoria", {}).get("Vencida") or 0) for c in data.clientes)

    story: list = []
    story.append(Spacer(1, 18 * mm))
    story.append(Paragraph("Cuentas Corrientes / Cobranzas", title))
    story.append(Paragraph(f"<b>Vendedor:</b> {data.vendedor_name}<br/><b>Generado:</b> {data.generated_at}", meta))

    # KPI table
    kpi_style = ParagraphStyle(
        "KPI",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
    )
    kpi_label = ParagraphStyle(
        "KPILabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6b7280"),
    )

    kpi_rows = [
        [
            Paragraph("CLIENTES", kpi_label),
            Paragraph("SALDO TOTAL", kpi_label),
            Paragraph("TOTAL VENCIDO", kpi_label),
        ],
        [
            Paragraph(str(clientes_count), kpi_style),
            Paragraph(_money_or_dash(saldo_total, format_number), kpi_style),
            Paragraph(f"<font color='#b91c1c'>{_money_or_dash(total_vencido, format_number)}</font>", kpi_style),
        ],
    ]
    kpi_table = Table(kpi_rows, colWidths=[60 * mm, 60 * mm, 60 * mm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#e5e7eb")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
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


def build_table(data: ReportData, format_number) -> list:
    styles = getSampleStyleSheet()
    client_style = ParagraphStyle(
        "ClientCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
    )
    code_style = ParagraphStyle(
        "ClientCode",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#6b7280"),
    )

    # Anchos fijos (puntos) para evitar encimado.
    # Requeridos por el usuario:
    col_widths = [180, 95, 95, 95, 95, 80]

    header = ["Cliente", "Saldo Total", "En Fecha", "Próximo", "Vencido", "Estado"]
    rows: list[list] = [header]

    # Ordenar por mayor vencido (desc)
    clientes_sorted = sorted(
        data.clientes,
        key=lambda c: float((c.get("saldos_por_categoria") or {}).get("Vencida") or 0),
        reverse=True,
    )

    total_saldo = 0.0
    total_vencido = 0.0

    estado_style = ParagraphStyle(
        "EstadoCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#111827"),
    )

    for c in clientes_sorted:
        name = c.get("CardName") or ""
        code = c.get("CardCode") or ""
        saldos = c.get("saldos_por_categoria") or {}
        saldo_total = c.get("CurrentAccountBalance") or 0
        en_fecha = saldos.get("En Fecha") or 0
        proximo = saldos.get("Proxima a Vencer") or 0
        vencido = saldos.get("Vencida") or 0
        mora = c.get("porcentaje_vencido") or 0

        estado = _estado_label(float(mora))

        client_cell = Paragraph(f"<b>{name}</b><br/><font color='#6b7280'>{code}</font>", client_style)
        estado_cell = Paragraph(f"<b>{estado}</b><br/>{int(round(float(mora)))}% mora", estado_style)

        try:
            total_saldo += float(saldo_total or 0)
        except (TypeError, ValueError):
            pass
        try:
            total_vencido += float(vencido or 0)
        except (TypeError, ValueError):
            pass

        rows.append(
            [
                client_cell,
                _money_or_dash(saldo_total, format_number),
                _money_or_dash(en_fecha, format_number),
                _money_or_dash(proximo, format_number),
                _money_or_dash(vencido, format_number),
                estado_cell,
            ]
        )

    # Fila final de totales
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

    table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")

    # Base style
    ts = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#6b7280")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#e5e7eb")),
            ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#eef2f7")),
        ]
    )

    # Requerimientos exactos para columnas numéricas:
    ts.add("FONTNAME", (1, 1), (4, -1), "Courier")
    ts.add("FONTSIZE", (1, 1), (4, -1), 8)
    ts.add("ALIGN", (1, 1), (4, -1), "RIGHT")

    # Cliente left
    ts.add("ALIGN", (0, 0), (0, -1), "LEFT")

    # Zebra rows (gris suave alternado) y estilo de columnas
    last_row_idx = len(rows) - 1
    for r in range(1, last_row_idx):
        if r % 2 == 0:
            ts.add("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f8fafc"))

    # Columna Vencido: fondo rojo muy suave + texto rojo oscuro + bold
    ts.add("BACKGROUND", (4, 1), (4, last_row_idx), colors.HexColor("#fef2f2"))
    ts.add("TEXTCOLOR", (4, 1), (4, last_row_idx), colors.HexColor("#991b1b"))
    ts.add("FONTNAME", (4, 1), (4, last_row_idx), "Courier-Bold")
    ts.add("FONTSIZE", (4, 1), (4, last_row_idx), 8.5)

    # Estado: color rojo si vencido (solo filas de datos)
    for r in range(1, last_row_idx):
        mora = float(clientes_sorted[r - 1].get("porcentaje_vencido") or 0)
        if mora >= 50:
            ts.add("TEXTCOLOR", (5, r), (5, r), colors.HexColor("#b91c1c"))
        elif mora >= 20:
            ts.add("TEXTCOLOR", (5, r), (5, r), colors.HexColor("#92400e"))

    # Totales: separación y énfasis
    ts.add("LINEABOVE", (0, last_row_idx), (-1, last_row_idx), 0.75, colors.HexColor("#e5e7eb"))
    ts.add("BACKGROUND", (0, last_row_idx), (-1, last_row_idx), colors.HexColor("#f3f4f6"))
    ts.add("FONTNAME", (0, last_row_idx), (-1, last_row_idx), "Helvetica-Bold")
    ts.add("ALIGN", (1, last_row_idx), (4, last_row_idx), "RIGHT")
    ts.add("FONTNAME", (1, last_row_idx), (4, last_row_idx), "Courier-Bold")
    ts.add("FONTSIZE", (1, last_row_idx), (4, last_row_idx), 8.5)

    table.setStyle(ts)

    return [table]


def generate_pdf_report(output_path: str, data: ReportData, format_number):
    # Si no entra en A4 vertical, cambiar inmediatamente a landscape(A4).
    col_widths = [180, 95, 95, 95, 95, 80]
    left_margin = 14 * mm
    right_margin = 14 * mm
    available_width_portrait = A4[0] - left_margin - right_margin
    page_size = A4
    if sum(col_widths) > available_width_portrait:
        page_size = landscape(A4)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=page_size,
        leftMargin=left_margin,
        rightMargin=right_margin,
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

