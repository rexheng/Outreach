"""Borough Briefing Pack — PDF generation from pre-computed JSON."""

import io
import json
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from api._config import DATA_DIR

TERRA = HexColor("#B5725A")
TERRA_DARK = HexColor("#6B4A3A")
CREAM = HexColor("#FAF7F3")
TEXT_PRIMARY = HexColor("#3D3530")
TEXT_MUTED = HexColor("#9A8E85")
BORDER = HexColor("#E5DDD5")

_briefing_data = None


def _load():
    global _briefing_data
    if _briefing_data is None:
        _briefing_data = json.loads((DATA_DIR / "briefing-data.json").read_text())
    return _briefing_data


def generate_pdf(borough_name: str) -> bytes | None:
    data = _load()
    # Case-insensitive lookup
    borough_key = None
    for name in data["boroughs"]:
        if name.lower() == borough_name.lower():
            borough_key = name
            break
    if borough_key is None:
        return None

    bd = data["boroughs"][borough_key]
    bstat = bd["stats"]
    london = data["london_averages"]
    ranking = data["borough_ranking"]

    rank = ranking.index(borough_key) + 1 if borough_key in ranking else len(ranking)
    total = len(ranking)

    buf = io.BytesIO()
    page_w, page_h = landscape(A4)
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=15 * mm, bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    elements = []

    style_title = ParagraphStyle("T", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=16, textColor=TERRA_DARK, spaceAfter=2)
    style_subtitle = ParagraphStyle("S", parent=styles["Normal"], fontName="Helvetica", fontSize=9, textColor=TEXT_MUTED, spaceAfter=8)
    style_section = ParagraphStyle("H", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=TERRA_DARK, spaceBefore=10, spaceAfter=4)
    style_body = ParagraphStyle("B", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, textColor=TEXT_PRIMARY, leading=13, spaceAfter=4)
    style_footer = ParagraphStyle("F", parent=styles["Normal"], fontName="Helvetica", fontSize=7, textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=6)

    # Header
    elements.append(Paragraph(f"Outreach \u2014 {borough_key}", style_title))
    elements.append(Paragraph("Mental Health Briefing", style_subtitle))
    rule = Table([[""]], colWidths=[page_w - 40 * mm], rowHeights=[1.5])
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TERRA)]))
    elements.append(rule)
    elements.append(Spacer(1, 6))

    # KPI row
    covid_change = bstat.get("samhi_covid_change", 0) or 0
    covid_arrow = "+" if covid_change >= 0 else ""
    kpi_data = [
        ["MEAN CNI SCORE", "BOROUGH RANK", "CRITICAL AREAS", "COVID IMPACT (SAMHI)"],
        [f"{bstat['mean_lri']:.1f} / 10", f"#{rank} of {total}", f"{bstat.get('critical_count', 0)}", f"{covid_arrow}{covid_change:.2f}"],
    ]
    col_w = (page_w - 40 * mm) / 4
    kpi_table = Table(kpi_data, colWidths=[col_w] * 4, rowHeights=[14, 28])
    kpi_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica"), ("FONTSIZE", (0, 0), (-1, 0), 7), ("TEXTCOLOR", (0, 0), (-1, 0), TEXT_MUTED),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (-1, 1), 14), ("TEXTCOLOR", (0, 1), (-1, 1), TERRA),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), CREAM), ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 8))

    # Priority Neighbourhoods
    elements.append(Paragraph("Priority Neighbourhoods", style_section))
    table_data = [["Neighbourhood", "CNI Score", "Tier", "Primary Driver"]]
    for row in bd["top5"]:
        table_data.append([Paragraph(row["lsoa_name"], style_body), str(row["lri_score"]), row["risk_tier"], row["dominant_pillar"]])
    t5_widths = [(page_w - 40 * mm) * w for w in [0.32, 0.14, 0.14, 0.40]]
    t5_table = Table(table_data, colWidths=t5_widths, repeatRows=1)
    t5_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), white), ("BACKGROUND", (0, 0), (-1, 0), TERRA_DARK),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_PRIMARY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, CREAM]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER), ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER),
        ("ALIGN", (1, 0), (2, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t5_table)
    elements.append(Spacer(1, 8))

    # Key Drivers
    elements.append(Paragraph("Key Drivers", style_section))
    critical_count = bd["critical_count"]
    if critical_count == 0:
        narrative = f"{borough_key} has no critical-need neighbourhoods. The mean CNI score is {bstat['mean_lri']:.1f}, ranking {rank} of {total} boroughs."
    else:
        socio_dominant = bd["socio_dominant_count"]
        demo_dominant = critical_count - socio_dominant
        if socio_dominant >= demo_dominant:
            driver_label = "socioeconomic deprivation indicators"
            driver_count = socio_dominant
        else:
            driver_label = "demographic vulnerability indicators"
            driver_count = demo_dominant
        narrative = f"{driver_label.capitalize().split(' ')[0]} factors are the primary driver in {borough_key}, with {driver_count} of {critical_count} critical-need neighbourhoods driven by {driver_label}."
        if bd["borough_antidep_mean"] > bd["london_antidep_mean"]:
            pct_above = ((bd["borough_antidep_mean"] - bd["london_antidep_mean"]) / bd["london_antidep_mean"]) * 100
            narrative += f" Antidepressant prescribing is {pct_above:.0f}% above the London average."
    elements.append(Paragraph(narrative, style_body))
    elements.append(Spacer(1, 6))

    # Borough vs London
    elements.append(Paragraph("Borough vs London", style_section))
    comp_data = [["Indicator", borough_key, "London Avg", "Difference"]]
    for label, key in [("CNI Score", "lri_score"), ("SAMHI Index (2022)", "samhi_index_2022"), ("Antidepressant Rate", "antidep_rate_2022"), ("Bad/Very Bad Health %", "health_bad_or_very_bad_pct"), ("IMD Score", "imd_score")]:
        lval = london.get(key, 0)
        bval_map = {"lri_score": "mean_lri", "samhi_index_2022": "samhi_mean", "antidep_rate_2022": "antidep_mean", "health_bad_or_very_bad_pct": "bad_health_mean", "imd_score": "imd_mean"}
        bval = bstat.get(bval_map[key], 0) or 0
        diff = bval - lval
        sign = "+" if diff >= 0 else ""
        comp_data.append([label, f"{bval:.2f}", f"{lval:.2f}", f"{sign}{diff:.2f}"])
    comp_widths = [(page_w - 40 * mm) * w for w in [0.35, 0.20, 0.20, 0.25]]
    comp_table = Table(comp_data, colWidths=comp_widths)
    comp_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), white), ("BACKGROUND", (0, 0), (-1, 0), TERRA_DARK),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_PRIMARY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, CREAM]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER), ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(comp_table)

    # Footer
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Data: IMD 2019, SAMHI 2022, Census 2021, ONS LSOA boundaries 2021. NaN values excluded from averages.", style_footer))
    elements.append(Paragraph("Generated by Outreach \u2014 The Geography of Wellbeing", style_footer))

    doc.build(elements)
    return buf.getvalue()
