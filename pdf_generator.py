import os
import io
from datetime import datetime
from typing import Dict, Any

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
(Score: {analysis_metrics.get('quality_score', 100)}/100 Grade: {analysis_metrics.get('grade', 'A')}) Tj
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
    Generates a professional code analysis report in PDF format branded with The Ram & Chisel.
    Returns the relative path to the generated PDF file.
    """
    if not output_filename:
        output_filename = os.path.join(REPORTS_DIR, f"ram_chisel_report_{analysis_id[:8]}.pdf")

    if not REPORTLAB_AVAILABLE:
        return _generate_fallback_pdf(analysis_id, analysis_metrics, price_charged, currency, output_filename)

    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=COLOR_BURGUNDY,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#5E4950')
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=COLOR_BURGUNDY,
        spaceBefore=10,
        spaceAfter=5
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=12,
        textColor=COLOR_DARK_TEXT
    )

    story = []

    # 1. Header with Logo & Brand
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        header_table_data = [
            [
                ReportLabImage(logo_path, width=48, height=54),
                [
                    Paragraph("<b>THE RAM & CHISEL</b>", title_style),
                    Paragraph("<b>Precision Code Quality & Security Audit</b>", subtitle_style),
                    Paragraph(
                        f"<b>Analysis ID:</b> {analysis_id} &nbsp;|&nbsp; <b>Date:</b> {datetime.utcnow().strftime('%B %d, %Y - %H:%M UTC')} &nbsp;|&nbsp; <b>Price:</b> ${price_charged:.2f} {currency}",
                        subtitle_style
                    )
                ]
            ]
        ]
        header_table = Table(header_table_data, colWidths=[60, 470])
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

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_GOLD, spaceAfter=14))

    # 2. Executive Scorecard Box
    grade = analysis_metrics.get("grade", "A")
    score = analysis_metrics.get("quality_score", 100)

    score_color = "#10B981" if score >= 80 else ("#D8A246" if score >= 60 else "#B91C1C")

    scorecard_data = [
        [
            Paragraph("<b>Overall Quality Score</b>", subtitle_style),
            Paragraph("<b>Audit Grade</b>", subtitle_style),
            Paragraph("<b>Analyzed Target</b>", subtitle_style)
        ],
        [
            Paragraph(f"<font size=18 color='{score_color}'><b>{score} / 100</b></font>", body_style),
            Paragraph(f"<font size=18 color='{score_color}'><b>Grade {grade}</b></font>", body_style),
            Paragraph(f"<b>{analysis_metrics.get('filename', 'Source Code')}</b>", body_style)
        ]
    ]

    scorecard_table = Table(scorecard_data, colWidths=[170, 170, 190])
    scorecard_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER_GOLD),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER_GOLD),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(scorecard_table)
    story.append(Spacer(1, 12))

    # 3. Volume & Structure Metrics
    story.append(Paragraph("📊 Volume & Structure Metrics", section_heading))
    metrics_data = [
        ["Metric", "Value", "Metric", "Value"],
        ["Total Lines of Code (LOC)", str(analysis_metrics.get("total_loc", 0)), "Functions / Methods", str(analysis_metrics.get("functions_count", 0))],
        ["Executable Code Lines", str(analysis_metrics.get("code_loc", 0)), "Classes / Structs", str(analysis_metrics.get("classes_count", 0))],
        ["Comment Lines", str(analysis_metrics.get("comment_lines", 0)), "Cyclomatic Complexity Score", str(analysis_metrics.get("complexity_score", 1.0))],
        ["Blank Lines", str(analysis_metrics.get("blank_lines", 0)), "AST Verification", "Passed" if analysis_metrics.get("ast_parsed") else "Pattern Matched"]
    ]

    metrics_table = Table(metrics_data, colWidths=[170, 95, 170, 95])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_BURGUNDY),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_GOLD),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER_GOLD),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG])
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 12))

    # 4. Security & Quality Findings
    story.append(Paragraph("🔍 Security & Maintainability Findings", section_heading))
    findings = analysis_metrics.get("findings", [])

    if not findings:
        story.append(Paragraph("✅ <i>No critical security issues or anti-patterns detected in the submitted code.</i>", body_style))
    else:
        findings_data = [["Severity", "Category", "Finding Details"]]
        for f in findings:
            sev = f.get("severity", "INFO")
            sev_color = "#B91C1C" if sev == "HIGH" else ("#D97706" if sev == "MEDIUM" else "#2563EB")
            findings_data.append([
                Paragraph(f"<font color='{sev_color}'><b>{sev}</b></font>", body_style),
                Paragraph(f.get("category", "General"), body_style),
                Paragraph(f.get("message", ""), body_style)
            ])

        findings_table = Table(findings_data, colWidths=[65, 115, 350])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_BURGUNDY),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_GOLD),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER_GOLD),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        story.append(findings_table)

    story.append(Spacer(1, 16))

    # 5. Privacy & Data Handling Guarantee
    privacy_box = [
        [
            Paragraph(
                "🔒 <b>The Ram & Chisel Privacy Guarantee:</b> We do not permanently retain source code after processing. "
                "Submitted source code is evaluated strictly in temporary working memory and purged upon report completion.",
                body_style
            )
        ]
    ]
    privacy_table = Table(privacy_box, colWidths=[530])
    privacy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER_GOLD),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10)
    ]))
    story.append(KeepTogether(privacy_table))

    # Build PDF
    doc.build(story)
    return output_filename
