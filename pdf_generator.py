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
        HRFlowable
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


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
<< /Length 120 >>
stream
BT
/F1 14 Tf
50 720 Td
(Code Analysis Report - ID: {analysis_id}) Tj
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
0000000405 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
478
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
    Generates a professional code analysis report in PDF format using ReportLab.
    Returns the relative path to the generated PDF file.
    """
    if not output_filename:
        output_filename = os.path.join(REPORTS_DIR, f"analysis_report_{analysis_id[:8]}.pdf")

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

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("🛡️ Code Quality & Security Audit Report", title_style))
    date_str = datetime.utcnow().strftime("%B %d, %Y - %H:%M UTC")
    story.append(Paragraph(
        f"<b>Analysis ID:</b> {analysis_id} &nbsp;|&nbsp; <b>Date:</b> {date_str} &nbsp;|&nbsp; <b>Price:</b> ${price_charged:.2f} {currency}",
        subtitle_style
    ))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=15))

    # 2. Executive Scorecard Box
    grade = analysis_metrics.get("grade", "A")
    score = analysis_metrics.get("quality_score", 100)

    score_color = colors.HexColor("#10B981") if score >= 80 else (colors.HexColor("#F59E0B") if score >= 60 else colors.HexColor("#EF4444"))

    scorecard_data = [
        [
            Paragraph("<b>Overall Quality Score</b>", subtitle_style),
            Paragraph("<b>Security & Health Grade</b>", subtitle_style),
            Paragraph("<b>Analyzed Target</b>", subtitle_style)
        ],
        [
            Paragraph(f"<font size=20 color='{score_color.hexval()}'><b>{score} / 100</b></font>", body_style),
            Paragraph(f"<font size=20 color='{score_color.hexval()}'><b>Grade {grade}</b></font>", body_style),
            Paragraph(f"<b>{analysis_metrics.get('filename', 'Source Code')}</b>", body_style)
        ]
    ]

    scorecard_table = Table(scorecard_data, colWidths=[170, 170, 190])
    scorecard_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(scorecard_table)
    story.append(Spacer(1, 15))

    # 3. Codebase Metrics
    story.append(Paragraph("📊 Volume & Structure Metrics", section_heading))
    metrics_data = [
        ["Metric", "Value", "Metric", "Value"],
        ["Total Lines of Code (LOC)", str(analysis_metrics.get("total_loc", 0)), "Functions / Methods", str(analysis_metrics.get("functions_count", 0))],
        ["Executable Code Lines", str(analysis_metrics.get("code_loc", 0)), "Classes / Structs", str(analysis_metrics.get("classes_count", 0))],
        ["Comment Lines", str(analysis_metrics.get("comment_lines", 0)), "Cyclomatic Complexity Score", str(analysis_metrics.get("complexity_score", 1.0))],
        ["Blank Lines", str(analysis_metrics.get("blank_lines", 0)), "AST Verification", "Passed" if analysis_metrics.get("ast_parsed") else "Regex Pattern Matched"]
    ]

    metrics_table = Table(metrics_data, colWidths=[170, 95, 170, 95])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 15))

    # 4. Security & Quality Findings
    story.append(Paragraph("🔍 Security & Maintainability Findings", section_heading))
    findings = analysis_metrics.get("findings", [])

    if not findings:
        story.append(Paragraph("✅ <i>No critical security issues or major anti-patterns detected in the submitted code.</i>", body_style))
    else:
        findings_data = [["Severity", "Category", "Finding Details"]]
        for f in findings:
            sev = f.get("severity", "INFO")
            sev_color = "#DC2626" if sev == "HIGH" else ("#D97706" if sev == "MEDIUM" else "#2563EB")
            findings_data.append([
                Paragraph(f"<font color='{sev_color}'><b>{sev}</b></font>", body_style),
                Paragraph(f.get("category", "General"), body_style),
                Paragraph(f.get("message", ""), body_style)
            ])

        findings_table = Table(findings_data, colWidths=[70, 110, 350])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        story.append(findings_table)

    story.append(Spacer(1, 20))

    # 5. Privacy & Data Handling Guarantee
    privacy_box = [
        [
            Paragraph(
                "🔒 <b>Data Privacy Guarantee:</b> We do not permanently retain source code after processing. "
                "Submitted source code is evaluated strictly in temporary working memory and purged upon report completion.",
                body_style
            )
        ]
    ]
    privacy_table = Table(privacy_box, colWidths=[530])
    privacy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12)
    ]))
    story.append(KeepTogether(privacy_table))

    # Build PDF
    doc.build(story)
    return output_filename
