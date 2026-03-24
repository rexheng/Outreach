"""Borough Briefing Pack — single-page PDF executive summary."""

import io
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from app.data.loader import load_and_prepare, BOROUGH_COL

router = APIRouter(prefix="/api")

# Brand colours
TERRA = HexColor("#B5725A")
TERRA_DARK = HexColor("#6B4A3A")
CREAM = HexColor("#FAF7F3")
TEXT_PRIMARY = HexColor("#3D3530")
TEXT_MUTED = HexColor("#9A8E85")
BORDER = HexColor("#E5DDD5")


def _get_borough_data(borough_name: str):
    """Look up borough from caches, return (borough_dict, borough_gdf, all_boroughs, full_gdf)."""
    _, gdf, borough_cache = load_and_prepare()

    borough_data = next(
        (b for b in borough_cache if b["borough"].lower() == borough_name.lower()),
        None,
    )
    if borough_data is None:
        return None

    borough_gdf = gdf[gdf[BOROUGH_COL].str.lower() == borough_name.lower()].copy()
    return borough_data, borough_gdf, borough_cache, gdf


def _compute_rank(borough_name: str, borough_cache: list) -> tuple[int, int]:
    """Return (rank, total) where rank 1 = highest need."""
    sorted_boroughs = sorted(borough_cache, key=lambda b: b["mean_lri"], reverse=True)
    total = len(sorted_boroughs)
    for i, b in enumerate(sorted_boroughs, 1):
        if b["borough"].lower() == borough_name.lower():
            return i, total
    return total, total


def _dominant_pillar(row) -> str:
    """Return human-readable label for the dominant pillar of an LSOA."""
    socio = row.get("pillar_socioeconomic", 0) or 0
    demo = row.get("pillar_demographic", 0) or 0
    return "Socioeconomic deprivation" if socio >= demo else "Demographic vulnerability"


def _build_narrative(borough_data: dict, borough_gdf, borough_cache: list, gdf) -> str:
    """Generate 2-3 sentence narrative from data."""
    borough = borough_data["borough"]
    critical = borough_gdf[borough_gdf["risk_tier"] == "Critical"]
    critical_count = len(critical)

    if critical_count == 0:
        rank, total = _compute_rank(borough, borough_cache)
        mean_cni = borough_data["mean_lri"]
        # Determine dominant pillar at borough level
        socio_mean = borough_gdf["pillar_socioeconomic"].mean()
        demo_mean = borough_gdf["pillar_demographic"].mean()
        dominant = "Socioeconomic factors" if socio_mean >= demo_mean else "Demographic factors"
        return (
            f"{borough} has no critical-need neighbourhoods. "
            f"The mean CNI score is {mean_cni:.1f}, ranking {rank} of {total} boroughs. "
            f"{dominant} account for the larger share of composite need."
        )

    # Count pillar dominance among critical LSOAs
    socio_dominant = (
        critical["pillar_socioeconomic"] > critical["pillar_demographic"]
    ).sum()
    demo_dominant = critical_count - socio_dominant

    if socio_dominant >= demo_dominant:
        driver_label = "socioeconomic deprivation indicators"
        driver_count = socio_dominant
    else:
        driver_label = "demographic vulnerability indicators"
        driver_count = demo_dominant

    narrative = (
        f"{driver_label.capitalize().split(' ')[0]} factors are the primary driver "
        f"in {borough}, with {driver_count} of {critical_count} critical-need "
        f"neighbourhoods driven by {driver_label}."
    )

    # Add notable indicator if above London average
    london_antidep = gdf["antidep_rate_2022"].mean()
    borough_antidep = borough_data.get("antidep_mean", 0) or 0
    if borough_antidep and london_antidep and borough_antidep > london_antidep:
        pct_above = ((borough_antidep - london_antidep) / london_antidep) * 100
        narrative += (
            f" Antidepressant prescribing is {pct_above:.0f}% above the London average."
        )

    return narrative


def _build_pdf(borough_data: dict, borough_gdf, borough_cache: list, gdf) -> bytes:
    """Build a single-page A4 landscape PDF and return bytes."""
    buf = io.BytesIO()
    page_w, page_h = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # -- Custom styles --
    style_title = ParagraphStyle(
        "BriefTitle", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=16, textColor=TERRA_DARK,
        spaceAfter=2,
    )
    style_subtitle = ParagraphStyle(
        "BriefSubtitle", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, textColor=TEXT_MUTED,
        spaceAfter=8,
    )
    style_section = ParagraphStyle(
        "SectionHead", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=9, textColor=TERRA_DARK,
        spaceBefore=10, spaceAfter=4,
        borderWidth=0, borderPadding=0,
    )
    style_body = ParagraphStyle(
        "BriefBody", parent=styles["Normal"],
        fontName="Helvetica", fontSize=8.5, textColor=TEXT_PRIMARY,
        leading=13, spaceAfter=4,
    )
    style_footer = ParagraphStyle(
        "BriefFooter", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7, textColor=TEXT_MUTED,
        alignment=TA_CENTER, spaceBefore=6,
    )

    borough = borough_data["borough"]
    rank, total = _compute_rank(borough, borough_cache)

    # ===== 1. HEADER =====
    elements.append(Paragraph(f"Outreach — {borough}", style_title))
    elements.append(Paragraph("Mental Health Briefing", style_subtitle))

    # Terracotta rule line via a thin table
    rule = Table([[""]], colWidths=[page_w - 40 * mm], rowHeights=[1.5])
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TERRA)]))
    elements.append(rule)
    elements.append(Spacer(1, 6))

    # ===== 2. KPI ROW =====
    covid_change = borough_data.get("samhi_covid_change", 0) or 0
    covid_arrow = "+" if covid_change >= 0 else ""
    kpi_data = [
        ["MEAN CNI SCORE", "BOROUGH RANK", "CRITICAL AREAS", "COVID IMPACT (SAMHI)"],
        [
            f"{borough_data['mean_lri']:.1f} / 10",
            f"#{rank} of {total}",
            f"{borough_data.get('critical_count', 0)}",
            f"{covid_arrow}{covid_change:.2f}",
        ],
    ]
    col_w = (page_w - 40 * mm) / 4
    kpi_table = Table(kpi_data, colWidths=[col_w] * 4, rowHeights=[14, 28])
    kpi_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("TEXTCOLOR", (0, 0), (-1, 0), TEXT_MUTED),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("TEXTCOLOR", (0, 1), (-1, 1), TERRA),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), CREAM),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 8))

    # ===== 3. TOP 5 PRIORITY NEIGHBOURHOODS =====
    elements.append(Paragraph("Priority Neighbourhoods", style_section))

    top5 = borough_gdf.nlargest(5, "lri_score")
    table_data = [["Neighbourhood", "CNI Score", "Tier", "Primary Driver"]]
    for _, row in top5.iterrows():
        name = row.get("lsoa_name") or row.get("lsoa_code", "Unknown")
        score = f"{row['lri_score']:.1f}"
        tier = row.get("risk_tier", "—")
        driver = _dominant_pillar(row)
        table_data.append([
            Paragraph(str(name), style_body),
            score,
            tier,
            driver,
        ])

    t5_widths = [
        (page_w - 40 * mm) * 0.32,
        (page_w - 40 * mm) * 0.14,
        (page_w - 40 * mm) * 0.14,
        (page_w - 40 * mm) * 0.40,
    ]
    t5_table = Table(table_data, colWidths=t5_widths, repeatRows=1)
    t5_table.setStyle(TableStyle([
        # Header row
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 0), (-1, 0), TERRA_DARK),
        # Body rows
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, CREAM]),
        # Grid
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t5_table)
    elements.append(Spacer(1, 8))

    # ===== 4. KEY DRIVERS NARRATIVE =====
    elements.append(Paragraph("Key Drivers", style_section))
    narrative = _build_narrative(borough_data, borough_gdf, borough_cache, gdf)
    elements.append(Paragraph(narrative, style_body))
    elements.append(Spacer(1, 6))

    # ===== 5. BOROUGH vs LONDON COMPARISON =====
    elements.append(Paragraph("Borough vs London", style_section))

    london_avgs = {
        "CNI Score": gdf["lri_score"].mean(),
        "SAMHI Index (2022)": gdf["samhi_index_2022"].mean(),
        "Antidepressant Rate": gdf["antidep_rate_2022"].mean(),
        "Bad/Very Bad Health %": gdf["health_bad_or_very_bad_pct"].mean(),
        "IMD Score": gdf["imd_score"].mean(),
    }
    borough_avgs = {
        "CNI Score": borough_data["mean_lri"],
        "SAMHI Index (2022)": borough_data.get("samhi_mean"),
        "Antidepressant Rate": borough_data.get("antidep_mean"),
        "Bad/Very Bad Health %": borough_data.get("bad_health_mean"),
        "IMD Score": borough_data.get("imd_mean"),
    }

    comp_data = [["Indicator", borough, "London Avg", "Difference"]]
    for indicator in london_avgs:
        london_val = london_avgs[indicator]
        borough_val = borough_avgs[indicator]
        if borough_val is not None and london_val is not None:
            diff = borough_val - london_val
            sign = "+" if diff >= 0 else ""
            comp_data.append([
                indicator,
                f"{borough_val:.2f}",
                f"{london_val:.2f}",
                f"{sign}{diff:.2f}",
            ])
        else:
            comp_data.append([indicator, "—", f"{london_val:.2f}" if london_val else "—", "—"])

    comp_widths = [
        (page_w - 40 * mm) * 0.35,
        (page_w - 40 * mm) * 0.20,
        (page_w - 40 * mm) * 0.20,
        (page_w - 40 * mm) * 0.25,
    ]
    comp_table = Table(comp_data, colWidths=comp_widths)
    comp_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 0), (-1, 0), TERRA_DARK),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, CREAM]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(comp_table)

    # ===== 6. FOOTER =====
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "Data: IMD 2019, SAMHI 2022, Census 2021, ONS LSOA boundaries 2021. "
        "NaN values excluded from averages.",
        style_footer,
    ))
    elements.append(Paragraph(
        "Generated by Outreach — The Geography of Wellbeing",
        style_footer,
    ))

    doc.build(elements)
    return buf.getvalue()


@router.get("/briefing/{borough_name}")
def borough_briefing(borough_name: str):
    """Generate and return a single-page PDF briefing for a borough."""
    result = _get_borough_data(borough_name)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Borough not found: {borough_name}",
        )

    borough_data, borough_gdf, borough_cache, gdf = result
    pdf_bytes = _build_pdf(borough_data, borough_gdf, borough_cache, gdf)

    # Sanitize filename
    safe_name = re.sub(r"[^a-zA-Z0-9]+", "-", borough_data["borough"]).strip("-")
    filename = f"Outreach-Briefing-{safe_name}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
