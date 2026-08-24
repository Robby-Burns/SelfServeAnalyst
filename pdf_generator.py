import os
import io
import zipfile
from datetime import datetime
from typing import Dict, Any, List

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        KeepTogether,
        HRFlowable,
        Image as ReportLabImage
    )
    REPORTLAB_AVAILABLE = True
    COLOR_BURGUNDY = colors.HexColor("#4A1525")
    COLOR_GOLD = colors.HexColor("#D8A246")
    COLOR_DARK_TEXT = colors.HexColor("#2A0B13")
    COLOR_LIGHT_BG = colors.HexColor("#FAF7F2")
    COLOR_BORDER_GOLD = colors.HexColor("#E5C378")
except ImportError:
    REPORTLAB_AVAILABLE = False
    COLOR_BURGUNDY = None
    COLOR_GOLD = None
    COLOR_DARK_TEXT = None
    COLOR_LIGHT_BG = None
    COLOR_BORDER_GOLD = None


def _generate_fallback_pdf(analysis_id: str, analysis_metrics: Dict[str, Any], price_charged: float, currency: str, output_filename: str):
    """Generates a minimal valid PDF binary if reportlab is not installed."""
    content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 140 >>
stream
BT
/F1 14 Tf
50 720 Td
(THE RAM & CHISEL - Code Analysis Report) Tj
0 -25 Td
(Analysis ID: {analysis_id}) Tj
0 -25 Td
(Price: ${price_charged:.2f} {currency}) Tj
0 -25 Td
(Language: {analysis_metrics.get('language', 'General')} LOC: {analysis_metrics.get('total_loc', 0)}) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000234 00000 n
0000000425 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
498
%%EOF"""
    with open(output_filename, "wb") as f:
        f.write(content.encode("utf-8"))
    return output_filename


def generate_analysis_pdf(
    analysis_id: str,
    analysis_metrics: Dict[str, Any],
    price_charged: float,
    currency: str = "USD",
    output_filename: str = None
) -> str:
    """
    Generates a professional code analysis report in PDF format matching the canonical 7-section design.
    Returns the relative/absolute path to the generated PDF file.
    """
    if not output_filename:
        filename_clean = re_sanitize(analysis_metrics.get("filename", "report"))
        output_filename = os.path.join(REPORTS_DIR, f"{filename_clean}_{analysis_id[:8]}.pdf")

    if not REPORTLAB_AVAILABLE:
        return _generate_fallback_pdf(analysis_id, analysis_metrics, price_charged, currency, output_filename)

    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=COLOR_BURGUNDY,
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#5E4950')
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=11,
        leading=15,
        textColor=COLOR_BURGUNDY,
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11.5,
        textColor=COLOR_DARK_TEXT
    )

    story = []

    # 1. Header with Logo & Brand
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        header_table_data = [
            [
                ReportLabImage(logo_path, width=44, height=50),
                [
                    Paragraph("<b>THE RAM & CHISEL</b>", title_style),
                    Paragraph("<b>Precision Code Quality, Security & Documentation Audit</b>", subtitle_style),
                    Paragraph(
                        f"<b>Target:</b> {os.path.basename(analysis_metrics.get('filename', 'Source Code'))} &nbsp;|&nbsp; <b>ID:</b> {analysis_id[:8]} &nbsp;|&nbsp; <b>Price:</b> ${price_charged:.2f} {currency}",
                        subtitle_style
                    )
                ]
            ]
        ]
        header_table = Table(header_table_data, colWidths=[55, 485])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
    else:
        story.append(Paragraph("THE RAM & CHISEL", title_style))
        story.append(Paragraph(
            f"<b>Analysis ID:</b> {analysis_id} &nbsp;|&nbsp; <b>Price:</b> ${price_charged:.2f} {currency}",
            subtitle_style
        ))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_GOLD, spaceAfter=10))

    # 2. Executive Summary Box (For Laymen & Stakeholders)
    exec_summary = analysis_metrics.get("exec_summary", "")
    posture = analysis_metrics.get("posture_status", "PRODUCTION READY")
    posture_color = "#DC2626" if "CRITICAL" in posture else ("#D97706" if "WARNING" in posture else "#166534")

    summary_box = [
        [
            Paragraph(f"<b>Executive Summary:</b> {exec_summary}<br/><b>Audit Posture:</b> <font color='{posture_color}'><b>{posture}</b></font>", body_style)
        ]
    ]
    summary_table = Table(summary_box, colWidths=[540])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER_GOLD),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 6))

    # 3. Scorecard Box (Clean Architecture & Code Metrics)
    scorecard_data = [
        [
            Paragraph("<b>Language Dialect</b>", subtitle_style),
            Paragraph("<b>Total LOC</b>", subtitle_style),
            Paragraph("<b>Executable Code</b>", subtitle_style),
            Paragraph("<b>Complexity Index</b>", subtitle_style)
        ],
        [
            Paragraph(f"<b>{analysis_metrics.get('language', 'General')}</b>", body_style),
            Paragraph(f"<b>{analysis_metrics.get('total_loc', 0)} lines</b>", body_style),
            Paragraph(f"<b>{analysis_metrics.get('code_loc', 0)} lines</b>", body_style),
            Paragraph(f"<b>{analysis_metrics.get('complexity_score', 1.0)}</b>", body_style)
        ]
    ]

    scorecard_table = Table(scorecard_data, colWidths=[135, 135, 135, 135])
    scorecard_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER_GOLD),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER_GOLD),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(scorecard_table)
    story.append(Spacer(1, 6))

    # 4. 7-Section Canonical Breakdown
    # 1. Overview & Data Flow
    story.append(Paragraph("1. Overview & Data Flow", section_heading))
    overview_text = (
        f"Source file <b>{os.path.basename(analysis_metrics.get('filename', ''))}</b> ({analysis_metrics.get('language', '')}) "
        f"contains {analysis_metrics.get('total_loc', 0)} total lines ({analysis_metrics.get('code_loc', 0)} executable) "
        f"with a cyclomatic complexity index of {analysis_metrics.get('complexity_score', 1.0)}."
    )
    story.append(Paragraph(overview_text, body_style))
    data_flow = analysis_metrics.get("data_flow")
    if data_flow:
        story.append(Paragraph(f"<b>Execution Pipeline:</b> {data_flow}", body_style))
    story.append(Spacer(1, 6))

    # 2. Business Logic & Component Responsibilities
    story.append(Paragraph("2. Business Logic & Component Responsibilities", section_heading))
    for bl in analysis_metrics.get("business_logic", []):
        story.append(Paragraph(f"• {bl}", body_style))
    story.append(Spacer(1, 6))

    # 3. Inputs & 4. Outputs
    story.append(Paragraph("3. Inputs & 4. Outputs", section_heading))
    inputs = analysis_metrics.get("inputs", [])
    outputs = analysis_metrics.get("outputs", [])
    io_text = f"<b>Inputs detected:</b> {len(inputs)} &nbsp;|&nbsp; <b>Outputs/Returns:</b> {len(outputs)}"
    story.append(Paragraph(io_text, body_style))
    story.append(Spacer(1, 6))

    # 5. Dependencies
    story.append(Paragraph("5. Dependencies & Integrations", section_heading))
    tp_deps = analysis_metrics.get("third_party_deps", [])
    sl_deps = analysis_metrics.get("stdlib_deps", [])
    tp_str = ", ".join(tp_deps) if tp_deps else "None (0 external packages)"
    story.append(Paragraph(f"<b>Third-Party Packages:</b> {tp_str}", body_style))
    if sl_deps:
        story.append(Paragraph(f"<b>Standard Library Modules:</b> {', '.join(sl_deps)}", body_style))
    story.append(Spacer(1, 6))

    # 6. Data Models & Persistence Structures
    story.append(Paragraph("6. Data Models & Persistence Structures", section_heading))
    d_models = analysis_metrics.get("data_models", [])
    if d_models:
        for dm in d_models:
            story.append(Paragraph(f"• {dm}", body_style))
    else:
        story.append(Paragraph("In-memory ephemeral state (no persistent tables or explicit entity models declared).", body_style))
    story.append(Spacer(1, 6))

    # 7. Best Practices Review & Actionable Security Audit
    story.append(Paragraph("7. Best Practices & Security Audit (SAST)", section_heading))
    bp = analysis_metrics.get("best_practices", {})
    story.append(Paragraph(f"• <b>Readability:</b> {bp.get('readability', 'Standard')}", body_style))
    story.append(Paragraph(f"• <b>Performance:</b> {bp.get('performance', 'Standard')}", body_style))
    story.append(Paragraph(f"• <b>Error Handling:</b> {bp.get('error_handling', 'Standard')}", body_style))
    story.append(Paragraph(f"• <b>Security Posture:</b> {bp.get('security', 'Standard')}", body_style))
    story.append(Paragraph(f"• <b>Maintainability:</b> {bp.get('maintainability', 'Standard')}", body_style))

    findings = analysis_metrics.get("findings", [])
    if findings:
        story.append(Spacer(1, 4))
        for f in findings:
            sev_color = "#DC2626" if f.get("severity") in ("CRITICAL", "HIGH") else "#D97706"
            line_str = f"Line {f.get('line')}: " if f.get("line") else ""
            story.append(Paragraph(f"• <font color='{sev_color}'><b>[{f.get('severity')}] {f.get('category')}</b></font> ({line_str}<code>{f.get('target', '')}</code>)", body_style))
            if f.get("business_risk"):
                story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>Business Risk:</b> <font color='#4B5563'><i>{f.get('business_risk')}</i></font>", body_style))
            if f.get("remediation"):
                story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>Remediation:</b> <font color='#1E40AF'><code>{f.get('remediation')}</code></font>", body_style))
            story.append(Spacer(1, 2))

    story.append(Spacer(1, 8))

    # Privacy Guarantee Footer
    privacy_box = [
        [
            Paragraph(
                "🔒 <b>The Ram & Chisel Privacy Guarantee:</b> Source code is processed strictly for analysis and is not permanently retained by the application.",
                body_style
            )
        ]
    ]
    privacy_table = Table(privacy_box, colWidths=[540])
    privacy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER_GOLD),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8)
    ]))
    story.append(KeepTogether(privacy_table))

    doc.build(story)
    return output_filename


def re_sanitize(name: str) -> str:
    """Sanitizes filename for filesystem safety."""
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def create_reports_zip(analysis_id: str, files_data: List[Dict[str, str]]) -> str:
    """
    Bundles all generated Markdown and PDF reports into a single ZIP archive.
    files_data: list of dicts with {'filename': ..., 'md_path': ..., 'pdf_path': ...}
    Returns path to created zip file.
    """
    zip_filename = os.path.join(REPORTS_DIR, f"ram_chisel_audit_{analysis_id[:8]}.zip")
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in files_data:
            if f.get("md_path") and os.path.exists(f["md_path"]):
                zipf.write(f["md_path"], arcname=os.path.basename(f["md_path"]))
            if f.get("pdf_path") and os.path.exists(f["pdf_path"]):
                zipf.write(f["pdf_path"], arcname=os.path.basename(f["pdf_path"]))
    return zip_filename
