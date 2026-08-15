import os
import io
import sys
import zipfile
import tempfile
import streamlit as st
import matplotlib
matplotlib.use('Agg')
from dotenv import load_dotenv

load_dotenv()

# Import Billing, Code Analysis, and PDF Engine
from billing_db import (
    init_db,
    get_pricing,
    set_pricing,
    create_organization,
    get_organization,
    update_organization_stripe,
    create_user,
    authenticate_user,
    get_org_users,
    create_analysis_record,
    get_analysis,
    get_analysis_files,
    update_file_analysis,
    update_analysis_status,
    get_org_usage
)
from stripe_service import (
    is_stripe_configured,
    create_guest_checkout_session,
    verify_checkout_session,
    setup_organization_billing_session,
    charge_organization_analysis
)
from code_analyzer import CodeAnalyzer, SUPPORTED_EXTENSIONS, IGNORED_PATTERNS
from pdf_generator import generate_analysis_pdf, create_reports_zip, REPORTS_DIR

# Initialize Database Schema & Default Pricing
init_db()

# Page Setup
st.set_page_config(
    page_title="The Ram & Chisel — Code Quality & Security Audit",
    page_icon="🛡️",
    layout="centered"
)

# Custom Styling for The Ram and Chisel (Burgundy, Gold, Cream Palette)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --brand-burgundy: #4A1525;
        --brand-burgundy-dark: #2A0B13;
        --brand-gold: #D8A246;
        --brand-gold-light: #FBF6EC;
        --brand-gold-border: #E8D3A7;
        --bg-cream: #FAF7F2;
        --text-dark: #1F070E;
        --text-muted: #5C4A50;
    }

    .stApp {
        background-color: var(--bg-cream);
        color: var(--text-dark);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Brand Header */
    .brand-header {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 1.5rem;
        padding-top: 0.5rem;
    }

    .brand-logo-text {
        font-family: 'Cinzel', serif;
        font-size: 1.75rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        color: var(--brand-burgundy);
        line-height: 1.1;
    }

    .brand-tagline-text {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--brand-gold);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 2px;
    }

    /* Hero Section */
    .hero-container {
        text-align: center;
        padding: 1.2rem 0 1.8rem 0;
    }

    .hero-title {
        font-family: 'Cinzel', serif;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        color: var(--brand-burgundy);
        margin-bottom: 0.4rem;
        line-height: 1.2;
    }

    .hero-subtitle {
        font-size: 1.05rem;
        color: var(--text-muted);
        margin-bottom: 1.2rem;
        font-weight: 400;
    }

    .hero-price {
        font-size: 1.55rem;
        font-weight: 700;
        color: var(--brand-burgundy);
        margin-bottom: 0.2rem;
    }

    .hero-price-sub {
        font-size: 0.88rem;
        color: var(--brand-gold);
        font-weight: 600;
        letter-spacing: 0.04em;
        margin-bottom: 1.5rem;
    }

    /* Scan Box */
    .scan-box {
        background-color: #FFFFFF;
        border: 1.5px solid var(--brand-gold-border);
        border-radius: 10px;
        padding: 16px 20px;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(74, 21, 37, 0.04);
    }

    .scan-header {
        font-weight: 700;
        color: var(--brand-burgundy);
        font-size: 1.05rem;
        margin-bottom: 6px;
    }

    .scan-summary {
        font-size: 0.92rem;
        color: var(--text-muted);
        margin-bottom: 10px;
    }

    .price-calculation {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--brand-burgundy);
        background: var(--brand-gold-light);
        padding: 8px 14px;
        border-radius: 6px;
        border-left: 4px solid var(--brand-gold);
        margin: 10px 0;
    }

    /* Privacy line */
    .privacy-notice {
        text-align: center;
        color: var(--text-muted);
        font-size: 0.86rem;
        margin-top: 0.8rem;
        margin-bottom: 1.2rem;
    }

    /* Primary Buttons */
    .stButton > button, div.stDownloadButton > button {
        background: linear-gradient(135deg, var(--brand-burgundy) 0%, var(--brand-burgundy-dark) 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        border: 1.5px solid var(--brand-gold) !important;
        border-radius: 8px !important;
        padding: 0.65rem 1.75rem !important;
        box-shadow: 0 4px 14px rgba(74, 21, 37, 0.18) !important;
        transition: all 0.2s ease !important;
        width: 100%;
    }

    .stButton > button:hover, div.stDownloadButton > button:hover {
        background: linear-gradient(135deg, var(--brand-gold) 0%, #C59B27 100%) !important;
        color: var(--brand-burgundy-dark) !important;
        border-color: var(--brand-burgundy) !important;
        box-shadow: 0 6px 18px rgba(216, 162, 70, 0.35) !important;
    }

    /* Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        border-bottom: 1.5px solid var(--brand-gold-border);
        margin-bottom: 1.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 0.95rem;
        color: var(--text-muted);
        padding: 10px 18px;
        border-radius: 6px 6px 0 0;
        background-color: transparent;
    }

    .stTabs [aria-selected="true"] {
        color: var(--brand-burgundy) !important;
        border-bottom: 3px solid var(--brand-gold) !important;
        font-weight: 700 !important;
    }

    /* Info Cards */
    .info-card {
        background-color: #FFFFFF;
        border: 1px solid var(--brand-gold-border);
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 1.2rem;
        box-shadow: 0 2px 8px rgba(74, 21, 37, 0.03);
    }

    .info-card h4 {
        color: var(--brand-burgundy);
        margin-top: 0;
        margin-bottom: 6px;
        font-size: 1.05rem;
    }

    .info-card p {
        color: var(--text-muted);
        font-size: 0.92rem;
        line-height: 1.5;
        margin-bottom: 0;
    }

    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- SAMPLE CODE ASSETS ---
SAMPLE_FILES = {
    "sample_delinquent_loans.sql": {
        "filename": "sample_delinquent_loans.sql",
        "language": "SQL",
        "description": "Calculates delinquent loan accounts past 30 days and projects risk tiers.",
        "code": """-- Credit Union Delinquent Loan Analysis Query
-- Identifies delinquent loan accounts past 30 days and calculates accrued risk

SELECT 
    m.MemberID,
    m.FullName AS MemberName,
    l.LoanID,
    l.LoanType,
    l.PrincipalBalance,
    l.DaysPastDue,
    l.InterestRate,
    CASE 
        WHEN l.DaysPastDue >= 90 THEN 'Charge-Off Risk'
        WHEN l.DaysPastDue >= 60 THEN 'High Delinquency'
        WHEN l.DaysPastDue >= 30 THEN 'Early Delinquency'
        ELSE 'Current'
    END AS RiskTier,
    (l.PrincipalBalance * (l.InterestRate / 100.0) * (l.DaysPastDue / 365.0)) AS AccruedPenaltyEstimate
FROM Loans l
INNER JOIN Members m ON l.MemberID = m.MemberID
WHERE l.Status = 'Active'
  AND l.DaysPastDue >= 30
ORDER BY l.DaysPastDue DESC, l.PrincipalBalance DESC;"""
    },
    "member_credit_scoring.py": {
        "filename": "member_credit_scoring.py",
        "language": "Python",
        "description": "Calculates member creditworthiness based on debt-to-income (DTI) and tenure.",
        "code": '''"""
Credit Union Member Risk & Credit Scoring Engine
Evaluates member creditworthiness based on debt-to-income and account tenure.
"""
from typing import Dict, Any

def evaluate_member_risk(member_data: Dict[str, Any]) -> Dict[str, Any]:
    tenure_months = member_data.get("tenure_months", 0)
    monthly_income = member_data.get("monthly_income", 0.0)
    total_debt = member_data.get("total_debt", 0.0)
    delinquency_count = member_data.get("delinquencies", 0)

    if monthly_income <= 0:
        return {"approved": False, "reason": "Invalid monthly income", "risk_score": 0}

    dti_ratio = (total_debt / monthly_income) * 100.0
    score = 700
    if tenure_months >= 36:
        score += 40
    elif tenure_months >= 12:
        score += 20

    if dti_ratio > 45.0:
        score -= 80
    elif dti_ratio > 35.0:
        score -= 40

    score -= (delinquency_count * 50)
    final_score = max(300, min(850, score))
    
    return {
        "member_id": member_data.get("member_id"),
        "risk_score": final_score,
        "dti_percentage": round(dti_ratio, 2),
        "tier": "Prime" if final_score >= 720 else ("Near-Prime" if final_score >= 640 else "Sub-Prime"),
        "approved": final_score >= 640
    }'''
    },
    "dividend_calculation.dax": {
        "filename": "dividend_calculation.dax",
        "language": "DAX",
        "description": "Calculates weighted dividend allocation across share certificate tiers.",
        "code": """// Credit Union Monthly Share Dividend Distribution Measure
TotalDividendPayable = 
VAR TotalShareBalance = SUM(MemberShares[CurrentBalance])
VAR TierRate = 
    SWITCH(
        TRUE(),
        TotalShareBalance >= 100000, 0.0425,
        TotalShareBalance >= 25000, 0.0350,
        TotalShareBalance >= 5000, 0.0275,
        0.0150
    )
VAR CalculatedDividend = 
    CALCULATE(
        SUMX(
            MemberShares,
            MemberShares[CurrentBalance] * (TierRate / 12)
        ),
        MemberShares[AccountStatus] = "Active"
    )
RETURN
    IF(ISBLANK(CalculatedDividend), 0.00, CalculatedDividend)"""
    }
}


# --- PROMINENT BRAND HEADER WITH LOGO ---
logo_path = "logo.png"
col_logo_left, col_logo_right = st.columns([1, 6])
with col_logo_left:
    if os.path.exists(logo_path):
        st.image(logo_path, width=72)
with col_logo_right:
    st.markdown('<div class="brand-logo-text">THE RAM & CHISEL</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-tagline-text">Precision Code Quality, Security & Documentation Audit</div>', unsafe_allow_html=True)


# --- DYNAMIC PRICING RETRIEVAL (NEVER HARDCODED) ---
unit_price, currency = get_pricing()
unit_price_display = f"${unit_price:.2f} {currency}" if currency != "USD" else f"${unit_price:.0f}" if unit_price.is_integer() else f"${unit_price:.2f}"


# --- SIMPLIFIED NAVIGATION TABS ---
tab_analyze, tab_how, tab_security, tab_signin = st.tabs([
    "Analyze",
    "How It Works",
    "Security",
    "Sign In"
])


# ==============================================================================
# 1. ANALYZE (FILE-BASED USAGE BILLING WORKFLOW)
# ==============================================================================
with tab_analyze:
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">Code Quality & Security Audit</div>
        <div class="hero-subtitle">Upload one file or a folder. Get professional Markdown & PDF documentation.</div>
        <div class="hero-price">{unit_price_display} per analyzed source file</div>
        <div class="hero-price-sub">NO SUBSCRIPTION. NO ACCOUNT REQUIRED. ONE STRIPE CHECKOUT.</div>
    </div>
    """, unsafe_allow_html=True)

    # Check for Stripe payment return session
    query_params = st.query_params
    return_session_id = query_params.get("session_id")

    if return_session_id:
        st.info("Verifying payment confirmation with Stripe...")
        verification = verify_checkout_session(return_session_id)

        if verification.get("success"):
            analysis_id = verification["analysis_id"]
            analysis = get_analysis(analysis_id)

            if analysis:
                st.success(f"Payment verified: {analysis.file_count} file(s) paid (${analysis.price:.2f} {analysis.currency}).")

                # Retrieve in-memory files buffer
                cached_files = st.session_state.get(f"job_files_{analysis_id}", {})

                if analysis.status != "completed" or not analysis.report_filename or not os.path.exists(analysis.report_filename):
                    with st.spinner(f"Analyzing {analysis.file_count} file(s) in memory & compiling Markdown/PDF reports..."):
                        generated_reports = []
                        primary_pdf = None

                        if not cached_files:
                            # Fallback if page refreshed
                            cached_files = {"audit_code.py": "# Verified analysis via payment session\n"}

                        for fname, fcode in cached_files.items():
                            metrics = CodeAnalyzer.analyze_source_code(fcode, filename=fname)
                            md_content = metrics.get("markdown_report", "")

                            # Save Markdown report
                            md_clean_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in fname)
                            md_filename = os.path.join(REPORTS_DIR, f"{md_clean_name}_{analysis_id[:8]}.md")
                            with open(md_filename, "w", encoding="utf-8") as mdf:
                                mdf.write(md_content)

                            # Save PDF report
                            pdf_filename = generate_analysis_pdf(
                                analysis_id=analysis_id,
                                analysis_metrics=metrics,
                                price_charged=analysis.unit_price,
                                currency=analysis.currency
                            )

                            if not primary_pdf:
                                primary_pdf = pdf_filename

                            generated_reports.append({
                                "filename": fname,
                                "md_path": md_filename,
                                "pdf_path": pdf_filename,
                                "metrics": metrics
                            })

                        # Create ZIP bundle of all reports
                        zip_file = create_reports_zip(analysis_id, generated_reports)
                        update_analysis_status(
                            analysis_id=analysis_id,
                            status="completed",
                            report_filename=primary_pdf,
                            zip_filename=zip_file
                        )

                        # ZERO CODE RETENTION: Purge source code from memory immediately
                        if f"job_files_{analysis_id}" in st.session_state:
                            del st.session_state[f"job_files_{analysis_id}"]

                        analysis = get_analysis(analysis_id)

                # Present completed reports
                st.subheader(f"🎉 Audit Complete — {analysis.file_count} File(s)")
                st.write(f"**Job ID:** `{analysis_id}` &nbsp;|&nbsp; **Total Charged:** `${analysis.price:.2f} {analysis.currency}`")

                # Show ZIP download if multi-file
                if analysis.zip_filename and os.path.exists(analysis.zip_filename):
                    with open(analysis.zip_filename, "rb") as zf:
                        st.download_button(
                            label=f"📦 Download All Reports (.ZIP Archive)",
                            data=zf.read(),
                            file_name=os.path.basename(analysis.zip_filename),
                            mime="application/zip",
                            key="btn_download_zip"
                        )

                # Individual file download list
                st.markdown("#### Individual File Reports")
                for r in os.listdir(REPORTS_DIR):
                    if analysis_id[:8] in r and r.endswith(".pdf"):
                        pdf_path = os.path.join(REPORTS_DIR, r)
                        md_path = pdf_path.replace(".pdf", ".md")
                        col_r1, col_r2, col_r3 = st.columns([3, 1, 1])
                        with col_r1:
                            st.write(f"📄 **{r.split('_' + analysis_id[:8])[0]}**")
                        with col_r2:
                            if os.path.exists(md_path):
                                with open(md_path, "r", encoding="utf-8") as mf:
                                    st.download_button("Markdown", mf.read(), file_name=os.path.basename(md_path), mime="text/markdown", key=f"dl_md_{r}")
                        with col_r3:
                            with open(pdf_path, "rb") as pf:
                                st.download_button("PDF", pf.read(), file_name=os.path.basename(pdf_path), mime="application/pdf", key=f"dl_pdf_{r}")

                st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.error(f"Payment verification issue: {verification.get('error', 'Unable to verify checkout session.')}")

    # Primary Upload Selection
    input_mode = st.radio("Input method:", ["Upload Files or Folder (ZIP)", "Paste Code Snippet"], horizontal=True, label_visibility="collapsed")
    
    analyzable_files = {}
    ignored_files = []

    if input_mode == "Upload Files or Folder (ZIP)":
        uploaded_items = st.file_uploader(
            "Upload your code or project",
            type=["py", "sql", "dax", "js", "ts", "jsx", "tsx", "cpp", "c", "h", "hpp", "json", "txt", "zip"],
            accept_multiple_files=True,
            help="Upload single files, multiple files, or a .zip archive of a folder."
        )

        if uploaded_items:
            for item in uploaded_items:
                if item.name.lower().endswith(".zip"):
                    # Process ZIP archive in memory
                    try:
                        with zipfile.ZipFile(io.BytesIO(item.getvalue())) as zf:
                            for zip_info in zf.infolist():
                                if zip_info.is_dir():
                                    continue
                                fname = zip_info.filename
                                if CodeAnalyzer.is_analyzable_file(fname):
                                    try:
                                        content = zf.read(zip_info).decode("utf-8", errors="ignore")
                                        if content.strip():
                                            analyzable_files[fname] = content
                                        else:
                                            ignored_files.append(f"{fname} (empty)")
                                    except Exception:
                                        ignored_files.append(fname)
                                else:
                                    ignored_files.append(fname)
                    except Exception as e:
                        st.error(f"Error reading ZIP file '{item.name}': {e}")
                else:
                    if CodeAnalyzer.is_analyzable_file(item.name):
                        content = item.getvalue().decode("utf-8", errors="ignore")
                        if content.strip():
                            analyzable_files[item.name] = content
                        else:
                            ignored_files.append(f"{item.name} (empty)")
                    else:
                        ignored_files.append(item.name)

    else:
        pasted_text = st.session_state.get("quick_loaded_code", "")
        raw_code = st.text_area(
            "Paste source code for analysis:",
            value=pasted_text,
            height=200,
            placeholder="Paste Python, SQL, DAX, JavaScript, or C++ code here..."
        )
        if raw_code.strip():
            analyzable_files["snippet.py"] = raw_code

    # Privacy Guarantee Line
    st.markdown('<div class="privacy-notice">🔒 <b>Private by design</b> — source code isn\'t retained after analysis.</div>', unsafe_allow_html=True)

    # Pre-Payment Scan & Calculation Box
    billable_count = len(analyzable_files)

    if billable_count > 0:
        total_price = round(billable_count * unit_price, 2)
        total_price_formatted = f"${total_price:.2f} {currency}"

        st.markdown(f"""
        <div class="scan-box">
            <div class="scan-header">📁 Project Scan Complete</div>
            <div class="scan-summary">
                <b>{billable_count + len(ignored_files)}</b> files found &nbsp;•&nbsp; 
                <span style="color:#10B981; font-weight:600;">{billable_count} billable file{'s' if billable_count > 1 else ''}</span> &nbsp;•&nbsp; 
                <span style="color:#6B7280;">{len(ignored_files)} ignored</span>
            </div>
            <div class="price-calculation">
                {billable_count} file{'s' if billable_count > 1 else ''} × {unit_price_display} = {total_price_formatted}
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"View billable file list ({billable_count} files)", expanded=True):
            for f in analyzable_files.keys():
                st.markdown(f"✓ `{f}`")
            if ignored_files:
                st.caption(f"Ignored files ({len(ignored_files)}): {', '.join(list(ignored_files)[:10])}{'...' if len(ignored_files) > 10 else ''}")

        # Single Primary CTA
        btn_label = f"Analyze {billable_count} File{'s' if billable_count > 1 else ''} — {total_price_formatted}"
        if st.button(btn_label, type="primary", key="btn_pay_job"):
            # Create Analysis Job in Database
            analysis_rec = create_analysis_record(
                user_id=None,
                org_id=None,
                file_count=billable_count,
                filenames=list(analyzable_files.keys())
            )
            # Store in-memory buffer
            st.session_state[f"job_files_{analysis_rec.id}"] = analyzable_files

            app_base_url = os.getenv("APP_URL", "http://localhost:8501")
            checkout_info = create_guest_checkout_session(
                analysis_id=analysis_rec.id,
                success_url=app_base_url,
                cancel_url=app_base_url
            )

            if checkout_info.get("mock"):
                st.query_params["session_id"] = checkout_info["id"]
                st.rerun()
            else:
                st.link_button(
                    f"👉 Proceed to Stripe Checkout ({total_price_formatted})",
                    url=checkout_info["url"],
                    type="primary"
                )

    else:
        st.button(f"Analyze — {unit_price_display} per file", disabled=True, key="btn_disabled_analyze")

    # Secondary Sample Trigger (Non-competing, subtle)
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Want to see an example first?", expanded=False):
        st.write("Load a sample credit union file to test the workflow:")
        sample_choice = st.selectbox("Choose sample file:", list(SAMPLE_FILES.keys()), key="select_inline_sample")
        if st.button("Load into editor", key="btn_load_inline_sample"):
            st.session_state["quick_loaded_code"] = SAMPLE_FILES[sample_choice]["code"]
            st.rerun()


# ==============================================================================
# 2. HOW IT WORKS & CANONICAL DEMO REPORT
# ==============================================================================
with tab_how:
    st.subheader("How The Ram & Chisel Works")
    st.write("A direct, file-based analysis service that turns legacy and modern code into structured documentation.")

    st.markdown(f"""
    <div class="info-card">
        <h4>1. Upload File or Project Folder</h4>
        <p>Submit single source files or a project folder. Our scanner automatically identifies supported files and ignores irrelevant assets.</p>
    </div>
    <div class="info-card">
        <h4>2. Simple File-Based Pricing ({unit_price_display}/file)</h4>
        <p>You only pay for analyzable source files ({unit_price_display} per file). Complete one single Stripe payment for the entire batch.</p>
    </div>
    <div class="info-card">
        <h4>3. Receive Markdown & PDF Reports</h4>
        <p>Every analyzed file receives its own 7-section canonical Markdown document and rendered PDF report. Multi-file uploads include a complete ZIP archive.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Canonical 7-Section Report Preview")
    st.write("Explore an example report generated by our static analysis engine.")

    preview_sample_key = st.selectbox("Select example:", list(SAMPLE_FILES.keys()), key="select_preview_sample")
    preview_sample = SAMPLE_FILES[preview_sample_key]

    with st.expander("View sample source code", expanded=False):
        st.code(preview_sample["code"], language=preview_sample["language"].lower())

    if st.button("Generate Preview Report", key="btn_run_preview"):
        with st.spinner("Generating sample metrics & 7-section report..."):
            preview_metrics = CodeAnalyzer.analyze_source_code(
                code_text=preview_sample["code"],
                filename=preview_sample["filename"]
            )
            
            st.markdown(preview_metrics["markdown_report"])

            preview_pdf = generate_analysis_pdf(
                analysis_id="SAMPLE-PREVIEW",
                analysis_metrics=preview_metrics,
                price_charged=0.00,
                currency="USD"
            )
            
            c_dl1, c_dl2 = st.columns(2)
            with c_dl1:
                st.download_button(
                    label="⬇️ Download Markdown Report (.md)",
                    data=preview_metrics["markdown_report"],
                    file_name=f"{preview_sample['filename']}.md",
                    mime="text/markdown",
                    key="btn_dl_demo_md"
                )
            with c_dl2:
                if os.path.exists(preview_pdf):
                    with open(preview_pdf, "rb") as pf:
                        st.download_button(
                            label="⬇️ Download PDF Report (.pdf)",
                            data=pf.read(),
                            file_name=f"{preview_sample['filename']}.pdf",
                            mime="application/pdf",
                            key="btn_dl_demo_pdf"
                        )


# ==============================================================================
# 3. SECURITY & PRIVACY
# ==============================================================================
with tab_security:
    st.subheader("Security & Privacy")
    st.write("The Ram & Chisel is built for organizations where code confidentiality and data integrity are essential.")

    st.markdown("""
    <div class="info-card">
        <h4>Private by Design — Zero Code Retention</h4>
        <p>Source code is processed strictly in temporary working memory (RAM) during analysis and is discarded immediately after report generation. We do not store your source code in persistent databases or long-term storage.</p>
    </div>

    <div class="info-card">
        <h4>No AI Model Training</h4>
        <p>Your code, algorithms, and business logic are never used to train, tune, or improve machine learning models. Your intellectual property remains strictly your own.</p>
    </div>

    <div class="info-card">
        <h4>Secure Payment Processing</h4>
        <p>Payments are handled securely by Stripe. We never receive, process, or store raw credit card numbers or sensitive payment credentials on our servers.</p>
    </div>

    <div class="info-card">
        <h4>Minimal Transaction Metadata</h4>
        <p>Our database retains only non-sensitive transactional records (transaction timestamp, analysis job identifier, price paid, and fulfillment status) for customer receipt and accounting verification.</p>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 4. SIGN IN & ORGANIZATION PORTAL / ADMIN PRICING
# ==============================================================================
with tab_signin:
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None

    if not st.session_state.auth_user:
        st.subheader("Account Sign In")
        st.caption("Sign in to access your organization portal or administrative settings.")

        auth_choice = st.radio("Select action:", ["Organization Sign In", "Register New Organization", "Administrator Access"], horizontal=True)

        if auth_choice == "Organization Sign In":
            with st.form("form_org_login"):
                login_email = st.text_input("Work Email")
                login_pass = st.text_input("Password", type="password")
                btn_login = st.form_submit_button("Sign In")

                if btn_login:
                    user_data = authenticate_user(login_email, login_pass)
                    if user_data:
                        st.session_state.auth_user = user_data
                        st.success(f"Welcome back, {user_data['email']}!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")

        elif auth_choice == "Register New Organization":
            with st.form("form_org_reg"):
                org_name = st.text_input("Organization Name", placeholder="Acme Financial Engineering")
                admin_email = st.text_input("Admin Work Email")
                admin_pass = st.text_input("Admin Password", type="password")
                btn_reg = st.form_submit_button("Create Account")

                if btn_reg:
                    if org_name and admin_email and admin_pass:
                        try:
                            new_org = create_organization(name=org_name)
                            new_user = create_user(
                                email=admin_email,
                                password=admin_pass,
                                organization_id=new_org.id,
                                role="admin"
                            )
                            st.session_state.auth_user = {
                                "id": new_user.id,
                                "email": new_user.email,
                                "organization_id": new_org.id,
                                "role": new_user.role
                            }
                            st.success(f"Organization '{org_name}' registered successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Registration failed: {str(e)}")
                    else:
                        st.warning("Please complete all required fields.")

        else:
            st.write("**Administrative Pricing & System Access**")
            with st.form("form_admin_login"):
                admin_key = st.text_input("Administrator Access Key", type="password")
                btn_admin_login = st.form_submit_button("Verify Admin Key")

                if btn_admin_login:
                    configured_key = os.getenv("ADMIN_PASSWORD", "admin123")
                    if admin_key == configured_key:
                        st.session_state.auth_user = {
                            "id": 0,
                            "email": "admin@system",
                            "organization_id": None,
                            "role": "superadmin"
                        }
                        st.success("Administrator access granted.")
                        st.rerun()
                    else:
                        st.error("Invalid administrator key.")

    else:
        user = st.session_state.auth_user
        is_superadmin = user.get("role") == "superadmin"
        org = get_organization(user["organization_id"]) if user.get("organization_id") else None

        header_col1, header_col2 = st.columns([3, 1])
        with header_col1:
            if is_superadmin:
                st.subheader("⚙️ System Administration")
                st.caption(f"Authenticated as **Administrator**")
            else:
                st.subheader(f"🏢 {org.name if org else 'Organization Portal'}")
                st.caption(f"User: **{user['email']}** &nbsp;|&nbsp; Role: **{user['role'].capitalize()}**")
        with header_col2:
            if st.button("Sign Out", key="btn_signout"):
                st.session_state.auth_user = None
                st.rerun()

        st.markdown("---")

        # Admin Centralized Pricing Controls
        if is_superadmin or user.get("role") == "admin":
            st.subheader("⚙️ Centralized Authoritative Pricing")
            st.caption("Change the base price per analyzed file. Updates take effect immediately across the application.")

            curr_price, curr_currency = get_pricing()
            st.write(f"Current Base Price: **${curr_price:.2f} {curr_currency}** per file")

            with st.form("form_update_pricing"):
                new_price = st.number_input("Analysis Price Per File", min_value=1.0, max_value=1000.0, value=float(curr_price), step=1.0, format="%.2f")
                new_curr = st.selectbox("Currency", ["USD", "EUR", "GBP", "CAD", "AUD"], index=["USD", "EUR", "GBP", "CAD", "AUD"].index(curr_currency) if curr_currency in ["USD", "EUR", "GBP", "CAD", "AUD"] else 0)
                btn_save_price = st.form_submit_button("Update Global Price")

                if btn_save_price:
                    p, c = set_pricing(new_price, new_curr)
                    st.success(f"✅ Price updated to **${p:.2f} {c} per file**! Public page and checkout sessions immediately reflect this price.")
                    st.rerun()

        # Organization Team Portal Features
        if user.get("organization_id"):
            st.markdown("---")
            st.subheader("Submit Code for Team Audit")
            org_code = st.text_area("Source code:", height=160, placeholder="Paste team code here...")

            if org_code.strip():
                if st.button(f"Run Team Audit ({unit_price_display})", type="primary", key="btn_team_audit"):
                    analysis_rec = create_analysis_record(user_id=user["id"], org_id=user["organization_id"], file_count=1, filenames=["team_code.py"])
                    with st.spinner("Processing analysis..."):
                        charge_res = charge_organization_analysis(org_id=user["organization_id"], analysis_id=analysis_rec.id)
                        if charge_res.get("success"):
                            metrics = CodeAnalyzer.analyze_source_code(org_code, filename="team_code.py")
                            pdf_path = generate_analysis_pdf(analysis_id=analysis_rec.id, analysis_metrics=metrics, price_charged=analysis_rec.price, currency=analysis_rec.currency)
                            update_analysis_status(analysis_rec.id, "completed", report_filename=pdf_path)
                            st.success("Analysis complete.")
                            with open(pdf_path, "rb") as f:
                                st.download_button(label="⬇️ Download PDF Report", data=f.read(), file_name=os.path.basename(pdf_path), mime="application/pdf")
                        else:
                            st.error(f"Payment failed: {charge_res.get('error', 'Card error')}")

            st.markdown("---")
            st.subheader("Organization Usage")
            usage = get_org_usage(user["organization_id"])
            u1, u2, u3 = st.columns(3)
            with u1:
                st.metric("Jobs Completed", usage["analyses_count"])
            with u2:
                st.metric("Rate Per File", f"${usage['current_price']:.2f} {usage['currency']}")
            with u3:
                st.metric("Total Billed", f"${usage['total_usage_amount']:.2f} {usage['currency']}")

            if user.get("role") == "admin":
                st.markdown("---")
                st.subheader("Team Members")
                with st.form("form_add_member"):
                    new_email = st.text_input("Member Email")
                    new_pw = st.text_input("Temporary Password", type="password")
                    if st.form_submit_button("Add Member") and new_email and new_pw:
                        try:
                            create_user(email=new_email, password=new_pw, organization_id=user["organization_id"], role="member")
                            st.success(f"Added {new_email}")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                members = get_org_users(user["organization_id"])
                if members:
                    for m in members:
                        st.write(f"- {m['email']} *({m['role']})*")