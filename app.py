import os
import io
import sys
import base64
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
    get_org_usage,
    get_user_usage,
    remove_user_from_org,
    update_user_role,
    reset_user_password
)
from stripe_service import (
    is_stripe_configured,
    create_guest_checkout_session,
    verify_checkout_session,
    setup_organization_billing_session,
    verify_setup_session,
    charge_organization_analysis
)
from code_analyzer import CodeAnalyzer, SUPPORTED_EXTENSIONS, IGNORED_PATTERNS
from pdf_generator import generate_analysis_pdf, create_reports_zip, REPORTS_DIR
from email_service import send_team_invite_email, is_email_configured

# Initialize Database Schema & Authoritative Pricing ($5.00 default)
init_db()

# Page Setup - Wide layout
st.set_page_config(
    page_title="The Ram & Chisel — Code Quality & Security Audit",
    layout="wide"
)

# Custom Styling (Deep Maroon, Burnished Gold & Clean Professional Typography — No Emojis)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800;900&family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --brand-maroon: #3D1220;
    --brand-maroon-dark: #240711;
    --brand-maroon-light: #521A2C;
    --brand-gold: #C9A24B;
    --brand-gold-light: #FAF4E8;
    --brand-gold-border: #E2CFAB;
    --brand-ember: #D9531E;
    --brand-ember-hover: #BF360C;
    --bg-cream: #FAF7F2;
    --bg-card: #FFFFFF;
    --text-dark: #1F070E;
    --text-muted: #5C4A50;
}

.stApp {
    background-color: var(--bg-cream);
    color: var(--text-dark);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.gold-divider {
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, var(--brand-gold) 35%, var(--brand-gold) 65%, transparent 100%);
    margin: 14px auto 20px auto;
    width: 85%;
    border: none;
}

/* Two-Column Hero Styling */
.hero-pitch-title {
    font-family: 'Cinzel', serif;
    font-size: 2.1rem;
    font-weight: 800;
    color: var(--brand-maroon);
    line-height: 1.2;
    margin-bottom: 0.6rem;
}

.hero-pitch-subtitle {
    font-size: 1.05rem;
    color: var(--text-muted);
    line-height: 1.5;
    margin-bottom: 1.2rem;
}

.price-pill {
    display: inline-flex;
    align-items: center;
    background: var(--brand-maroon);
    border: 2px solid var(--brand-gold);
    border-radius: 30px;
    padding: 8px 18px;
    color: var(--brand-gold-light);
    font-weight: 700;
    font-size: 1.05rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 4px 12px rgba(61, 18, 32, 0.12);
}

.price-pill b {
    color: #FFFFFF;
    font-size: 1.15rem;
}

/* Upload Zone */
.upload-card-wrapper {
    background: var(--bg-card);
    border: 2px dashed var(--brand-gold);
    border-radius: 12px;
    padding: 22px 20px;
    text-align: center;
    box-shadow: 0 4px 16px rgba(61, 18, 32, 0.04);
    transition: all 0.2s ease;
}

.upload-card-wrapper:hover {
    border-color: var(--brand-ember);
    box-shadow: 0 6px 20px rgba(217, 83, 30, 0.1);
}

.upload-title {
    font-family: 'Cinzel', serif;
    font-weight: 700;
    font-size: 1.2rem;
    color: var(--brand-maroon);
    margin-bottom: 4px;
}

.upload-sub {
    font-size: 0.88rem;
    color: var(--text-muted);
    margin-bottom: 10px;
}

.supported-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: center;
    margin-top: 10px;
}

.badge-tag {
    background: var(--brand-gold-light);
    border: 1px solid var(--brand-gold-border);
    color: var(--brand-maroon);
    font-size: 0.75rem;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 4px;
}

/* Scan Result Box */
.scan-summary-card {
    background: #FFFFFF;
    border: 1.5px solid var(--brand-gold-border);
    border-radius: 10px;
    padding: 16px 20px;
    margin: 1.2rem 0;
    box-shadow: 0 3px 10px rgba(61, 18, 32, 0.05);
}

.scan-summary-header {
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--brand-maroon);
}

.price-calculation-callout {
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--brand-maroon);
    background: var(--brand-gold-light);
    padding: 10px 16px;
    border-radius: 8px;
    border-left: 5px solid var(--brand-gold);
    margin: 12px 0;
}

/* Hallmark Certificate Badge (Accuracy Confidence Score) */
.hallmark-container {
    background: linear-gradient(135deg, #FAF4E8 0%, #FFFFFF 100%);
    border: 2px solid var(--brand-gold);
    border-radius: 12px;
    padding: 18px 24px;
    margin: 1.5rem 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 16px rgba(201, 162, 75, 0.12);
}

.hallmark-details h3 {
    margin: 0;
    font-family: 'Cinzel', serif;
    font-size: 1.35rem;
    color: var(--brand-maroon);
}

.hallmark-details p {
    margin: 2px 0 0 0;
    font-size: 0.88rem;
    color: var(--text-muted);
}

.confidence-chip {
    padding: 6px 18px;
    border-radius: 30px;
    font-weight: 800;
    font-size: 1.05rem;
    letter-spacing: 0.02em;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.conf-high {
    background: #E8F5E9;
    color: #1B5E20;
    border: 1.5px solid #81C784;
}

.conf-mod {
    background: #FFF8E1;
    color: #F57F17;
    border: 1.5px solid #FFD54F;
}

.conf-low {
    background: #FFEBEE;
    color: #B71C1C;
    border: 1.5px solid #E57373;
}

/* Primary Marketing / Checkout Button (Ember Highlight) */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand-ember) 0%, var(--brand-ember-hover) 100%) !important;
    color: #FFFFFF !important;
    font-weight: 800 !important;
    font-size: 1.05rem !important;
    letter-spacing: 0.02em !important;
    border: 1.5px solid #FF8A65 !important;
    border-radius: 8px !important;
    padding: 0.75rem 2rem !important;
    box-shadow: 0 6px 18px rgba(217, 83, 30, 0.25) !important;
    transition: all 0.2s ease !important;
    width: 100%;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #FF6D00 0%, #D9531E 100%) !important;
    box-shadow: 0 8px 24px rgba(217, 83, 30, 0.38) !important;
    transform: translateY(-1px);
}

/* In-Product Action Buttons */
.stButton > button:not([kind="primary"]), div.stDownloadButton > button {
    background: var(--brand-maroon) !important;
    color: var(--brand-gold-light) !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    border: 1px solid var(--brand-gold) !important;
    border-radius: 6px !important;
    padding: 0.5rem 1.2rem !important;
    box-shadow: 0 2px 6px rgba(61, 18, 32, 0.1) !important;
    transition: all 0.15s ease !important;
    width: 100%;
}

.stButton > button:not([kind="primary"]):hover, div.stDownloadButton > button:hover {
    background: var(--brand-maroon-light) !important;
    border-color: #FFFFFF !important;
    color: #FFFFFF !important;
}

/* Tabs Navigation */
.stTabs [data-baseweb="tab-list"] {
    gap: 12px;
    border-bottom: 2px solid var(--brand-gold-border);
    margin-bottom: 1.6rem;
}

.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    font-size: 0.98rem;
    color: var(--text-muted);
    padding: 10px 18px;
    border-radius: 6px 6px 0 0;
    background-color: transparent;
}

.stTabs [aria-selected="true"] {
    color: var(--brand-maroon) !important;
    border-bottom: 3.5px solid var(--brand-gold) !important;
    font-weight: 800 !important;
}

/* Card Box */
.info-card {
    background-color: #FFFFFF;
    border: 1px solid var(--brand-gold-border);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 1.2rem;
    box-shadow: 0 2px 8px rgba(61, 18, 32, 0.03);
}

.info-card h4 {
    color: var(--brand-maroon);
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

/* Report Card Container */
.report-card {
    background: #FFFFFF;
    border: 1.5px solid var(--brand-gold-border);
    border-radius: 10px;
    padding: 24px;
    margin-top: 1rem;
    box-shadow: 0 4px 14px rgba(61, 18, 32, 0.05);
}

.privacy-notice {
    text-align: center;
    color: var(--text-muted);
    font-size: 0.86rem;
    margin-top: 0.8rem;
    margin-bottom: 1.2rem;
}

header {visibility: hidden;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- SAMPLE CODE ASSETS FOR PREVIEW TAB ---
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


# --- PROMINENT LOGO & BRAND HEADER (PERFECTLY CENTERED) ---
logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
logo_img_tag = ""
if os.path.exists(logo_path):
    try:
        with open(logo_path, "rb") as f:
            b64_logo = base64.b64encode(f.read()).decode("utf-8")
            logo_img_tag = f'<img src="data:image/png;base64,{b64_logo}" style="width: 115px; margin: 0 auto 8px auto; display: block;">'
    except Exception:
        pass

st.markdown(f"""
<div style="text-align: center; margin: 0 auto 1.4rem auto; width: 100%;">
{logo_img_tag}
<div style="font-family: 'Cinzel', serif; font-size: 2.2rem; font-weight: 900; letter-spacing: 0.08em; color: #3D1220; line-height: 1.1; margin-top: 4px; text-align: center;">THE RAM & CHISEL</div>
<div style="font-size: 0.88rem; font-weight: 700; color: #C9A24B; text-transform: uppercase; letter-spacing: 0.16em; margin-top: 4px; text-align: center;">Precision Code Quality, Security &amp; Documentation Audit</div>
<hr style="height: 2px; background: linear-gradient(90deg, transparent 0%, #C9A24B 35%, #C9A24B 65%, transparent 100%); margin: 14px auto 20px auto; width: 85%; border: none;">
</div>
""", unsafe_allow_html=True)


# --- DYNAMIC PRICING RETRIEVAL ($5.00) ---
unit_price, currency = get_pricing()
unit_price_display = f"${unit_price:.2f} {currency}" if currency != "USD" else f"${unit_price:.0f}" if unit_price.is_integer() else f"${unit_price:.2f}"

# --- SESSION STATE & PERSISTENT USER HEADER ---
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

current_auth = st.session_state.get("auth_user")
current_org = get_organization(current_auth["organization_id"]) if (current_auth and current_auth.get("organization_id")) else None

if current_auth:
    org_tag = f" &nbsp;•&nbsp; <b>{current_org.name}</b>" if current_org else " &nbsp;•&nbsp; Personal Account"
    role_tag = f" <i>({current_auth.get('role').capitalize()})</i>" if current_auth.get("role") else ""
    
    top_c1, top_c2 = st.columns([5, 1])
    with top_c1:
        st.markdown(f"""
        <div style="background: #FAF7F2; border: 1px solid #E5C378; border-radius: 8px; padding: 7px 14px; margin-bottom: 10px; font-size: 0.88rem; color: #3D1220;">
            Signed in as: <b>{current_auth['email']}</b>{role_tag}{org_tag}
        </div>
        """, unsafe_allow_html=True)
    with top_c2:
        if st.button("Sign Out", key="top_global_signout"):
            st.session_state.auth_user = None
            st.rerun()

signin_tab_label = "Dashboard & Account" if current_auth else "Sign In"

# --- CLEAN NAVIGATION TABS (NO EMOJIS) ---
tab_analyze, tab_preview, tab_how, tab_security, tab_signin = st.tabs([
    "Analyze Code",
    "Example Preview",
    "How It Works",
    "Security & Privacy",
    signin_tab_label
])


# ==============================================================================
# 1. ANALYZE (TWO-COLUMN HERO & FILE/FOLDER UPLOAD ONLY)
# ==============================================================================
with tab_analyze:
    # Check for Stripe payment return session
    query_params = st.query_params
    return_session_id = query_params.get("session_id")
    return_setup_id = query_params.get("setup_session_id")

    if return_setup_id:
        st.info("Verifying corporate payment method with Stripe...")
        setup_verif = verify_setup_session(return_setup_id)
        if setup_verif.get("success"):
            st.success("Corporate payment method saved and synced successfully!")
        else:
            st.error(f"Could not link payment method: {setup_verif.get('error')}")

    if return_session_id:
        st.info("Verifying payment confirmation with Stripe...")
        verification = verify_checkout_session(return_session_id)

        if verification.get("success"):
            analysis_id = verification["analysis_id"]
            analysis = get_analysis(analysis_id)

            if analysis:
                st.success(f"Payment verified: {analysis.file_count} file(s) paid (${analysis.price:.2f} {analysis.currency}).")

                cached_files = st.session_state.get(f"job_files_{analysis_id}", {})

                if analysis.status != "completed" or not analysis.report_filename or not os.path.exists(analysis.report_filename):
                    with st.spinner(f"Analyzing {analysis.file_count} file(s) in memory & compiling reports..."):
                        generated_reports = []
                        primary_pdf = None

                        if not cached_files:
                            cached_files = {"audit_source.py": "# Verified analysis via payment session\n"}

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

                        # Create ZIP bundle
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
                st.subheader(f"Audit Complete — {analysis.file_count} File(s)")
                st.write(f"**Job ID:** `{analysis_id}` &nbsp;|&nbsp; **Total Charged:** `${analysis.price:.2f} {analysis.currency}`")

                if analysis.zip_filename and os.path.exists(analysis.zip_filename):
                    with open(analysis.zip_filename, "rb") as zf:
                        st.download_button(
                            label="Download All Reports (.ZIP Archive)",
                            data=zf.read(),
                            file_name=os.path.basename(analysis.zip_filename),
                            mime="application/zip",
                            key="btn_download_zip"
                        )

                st.markdown("#### Technical Audit Reports")
                for r in os.listdir(REPORTS_DIR):
                    if analysis_id[:8] in r and r.endswith(".pdf"):
                        pdf_path = os.path.join(REPORTS_DIR, r)
                        md_path = pdf_path.replace(".pdf", ".md")
                        col_r1, col_r2, col_r3 = st.columns([3, 1, 1])
                        with col_r1:
                            st.write(f"**{r.split('_' + analysis_id[:8])[0]}**")
                        with col_r2:
                            if os.path.exists(md_path):
                                with open(md_path, "r", encoding="utf-8") as mf:
                                    st.download_button("Markdown", mf.read(), file_name=os.path.basename(md_path), mime="text/markdown", key=f"dl_md_{r}")
                        with col_r3:
                            with open(pdf_path, "rb") as pf:
                                st.download_button("PDF Report", pf.read(), file_name=os.path.basename(pdf_path), mime="application/pdf", key=f"dl_pdf_{r}")

                st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
        else:
            st.error(f"Payment verification issue: {verification.get('error', 'Unable to verify checkout session.')}")

    # --- TWO-COLUMN HERO LAYOUT ---
    col_pitch, col_upload = st.columns([1.1, 1.0], gap="large")

    with col_pitch:
        st.markdown('<div class="hero-pitch-title">Precision Craftsmanship Applied to Code Audits</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-pitch-subtitle">Submit raw source code or legacy projects. Receive rigorous security evaluations, architectural insights, and certified PDF documentation.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="price-pill"><b>{unit_price_display} per analyzed file</b> &nbsp;•&nbsp; Transparent Batch Billing &nbsp;•&nbsp; No Subscription Lock-In</div>', unsafe_allow_html=True)
        
        st.markdown("""
<div class="info-card" style="margin-top: 0.6rem;">
<h4 style="color: #3D1220; margin-top: 0; margin-bottom: 6px; font-size: 1.05rem;">7-Section Canonical Documentation</h4>
<p style="color: #5C4A50; font-size: 0.92rem; line-height: 1.5; margin-bottom: 0;">Every analyzed file receives a complete overview, business logic extraction, input/output mappings, external dependencies, data relationships, and best practice recommendations in Markdown and PDF.</p>
</div>
""", unsafe_allow_html=True)

    with col_upload:
        st.markdown("""
        <div class="upload-card-wrapper">
            <div class="upload-title">Upload Source Files or Project ZIP</div>
            <div class="upload-sub">Drag & drop files or project archive for instant analysis</div>
            <div class="supported-badges">
                <span class="badge-tag">.PY</span>
                <span class="badge-tag">.SQL</span>
                <span class="badge-tag">.DAX</span>
                <span class="badge-tag">.JS/.TS</span>
                <span class="badge-tag">.CPP</span>
                <span class="badge-tag">.JSON</span>
                <span class="badge-tag">.ZIP</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if current_auth:
            if current_org:
                st.markdown(f"<div style='background:#FAF7F2; border:1px solid #E5C378; border-radius:6px; padding:6px 12px; margin-bottom:10px; font-size:0.84rem; color:#3D1220;'>🏢 Organization: <b>{current_org.name}</b> &nbsp;|&nbsp; Audits are attributed to your team account.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background:#FAF7F2; border:1px solid #E5C378; border-radius:6px; padding:6px 12px; margin-bottom:10px; font-size:0.84rem; color:#3D1220;'>👤 Personal Account: <b>{current_auth['email']}</b> &nbsp;|&nbsp; Reports will be saved to your account.</div>", unsafe_allow_html=True)

        uploaded_items = st.file_uploader(
            "Upload files or project folder (.zip)",
            type=["py", "sql", "dax", "js", "ts", "jsx", "tsx", "cpp", "c", "h", "hpp", "json", "txt", "zip"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            help="Upload single files, multiple files, or a .zip archive of a folder."
        )

        analyzable_files = {}
        ignored_files = []

        if uploaded_items:
            for item in uploaded_items:
                if item.name.lower().endswith(".zip"):
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

        billable_count = len(analyzable_files)

        if billable_count > 0:
            total_price = round(billable_count * unit_price, 2)
            total_price_formatted = f"${total_price:.2f} {currency}"

            st.markdown(f"""
            <div class="scan-summary-card">
                <div class="scan-summary-header">
                    <span>Project Scan Complete</span>
                </div>
                <p style="margin:4px 0 0 0; color:#5C4A50; font-size:0.9rem;">
                    <b>{billable_count + len(ignored_files)}</b> files inspected &nbsp;•&nbsp; 
                    <span style="color:#10B981; font-weight:700;">{billable_count} billable</span> &nbsp;•&nbsp; 
                    <span style="color:#6B7280;">{len(ignored_files)} ignored</span>
                </p>
                <div class="price-calculation-callout">
                    {billable_count} file{'s' if billable_count > 1 else ''} × {unit_price_display} = {total_price_formatted}
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"Inspected billable file list ({billable_count} files)", expanded=False):
                for f in analyzable_files.keys():
                    st.markdown(f"✓ `{f}`")
                if ignored_files:
                    st.caption(f"Ignored non-source assets ({len(ignored_files)}): {', '.join(list(ignored_files)[:8])}...")

            # High-Impact Checkout Button
            btn_label = f"Analyze {billable_count} File{'s' if billable_count > 1 else ''} — {total_price_formatted}"
            if st.button(btn_label, type="primary", key="btn_pay_job"):
                logged_in = st.session_state.get("auth_user")
                cur_user_id = logged_in.get("id") if (logged_in and logged_in.get("id") != 0) else None
                cur_org_id = logged_in.get("organization_id") if logged_in else None

                analysis_rec = create_analysis_record(
                    user_id=cur_user_id,
                    org_id=cur_org_id,
                    file_count=billable_count,
                    filenames=list(analyzable_files.keys())
                )
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
                        f"Proceed to Stripe Checkout ({total_price_formatted})",
                        url=checkout_info["url"],
                        type="primary"
                    )

        else:
            st.button(f"Analyze — {unit_price_display} per file", disabled=True, key="btn_disabled_analyze")

        st.markdown('<div class="privacy-notice">Private by design — source code is evaluated in-memory and never stored.</div>', unsafe_allow_html=True)


# ==============================================================================
# 2. EXAMPLE PREVIEW (STRUCTURED PROOF OF VALUE)
# ==============================================================================
with tab_preview:
    st.subheader("Report Preview & Sample Audits")
    st.write("Examine the exact 7-section technical documentation report produced for legacy and modern files.")

    col_demo_select, col_demo_btn = st.columns([3, 1])
    with col_demo_select:
        selected_sample_name = st.selectbox(
            "Choose a domain sample file:",
            list(SAMPLE_FILES.keys()),
            key="preview_sample_selector"
        )
    sample_data = SAMPLE_FILES[selected_sample_name]

    st.info(f"**Target:** `{sample_data['filename']}` ({sample_data['language']}) — {sample_data['description']}")

    with st.expander("View Sample Source Code (Raw Input)", expanded=False):
        st.code(sample_data["code"], language=sample_data["language"].lower())

    with col_demo_btn:
        st.write("")
        st.write("")
        run_preview = st.button("Generate Preview Report", key="btn_generate_preview")

    if run_preview:
        with st.spinner("Compiling 7-section report..."):
            metrics = CodeAnalyzer.analyze_source_code(
                code_text=sample_data["code"],
                filename=sample_data["filename"]
            )

            # Accuracy Confidence Score Badge Component
            conf_score = metrics.get('quality_score', 100)
            conf_tier = "High Confidence" if conf_score >= 80 else ("Moderate Confidence" if conf_score >= 60 else "Review Required")
            conf_chip_class = "conf-high" if conf_score >= 80 else ("conf-mod" if conf_score >= 60 else "conf-low")

            st.markdown(f"""
            <div class="hallmark-container">
                <div class="hallmark-details">
                    <h3>{metrics.get('filename', sample_data['filename'])}</h3>
                    <p>Language: <b>{metrics.get('language', 'General')}</b> &nbsp;|&nbsp; Volume: <b>{metrics.get('total_loc', 0)} LOC</b> &nbsp;|&nbsp; Complexity: <b>{metrics.get('complexity_score', 1.0)}</b></p>
                </div>
                <div>
                    <span class="confidence-chip {conf_chip_class}">Accuracy Confidence Score: {conf_score}% ({conf_tier})</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Clear Visual Card Boundary for Report Body
            st.markdown('<div class="report-card">', unsafe_allow_html=True)
            st.markdown(metrics["markdown_report"])
            st.markdown('</div>', unsafe_allow_html=True)

            sample_pdf_path = generate_analysis_pdf(
                analysis_id="SAMPLE-DEMO",
                analysis_metrics=metrics,
                price_charged=0.00,
                currency="USD"
            )

            st.markdown("<br>", unsafe_allow_html=True)
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                st.download_button(
                    label="Download Markdown Report (.md)",
                    data=metrics["markdown_report"],
                    file_name=f"{sample_data['filename']}.md",
                    mime="text/markdown",
                    key="btn_dl_sample_md"
                )
            with c_btn2:
                if os.path.exists(sample_pdf_path):
                    with open(sample_pdf_path, "rb") as pf:
                        st.download_button(
                            label="Download PDF Report (.pdf)",
                            data=pf.read(),
                            file_name=f"sample_{sample_data['filename']}.pdf",
                            mime="application/pdf",
                            key="btn_dl_sample_pdf"
                        )


# ==============================================================================
# 3. HOW IT WORKS
# ==============================================================================
with tab_how:
    st.subheader("How It Works")
    st.write("Precision craftsmanship applied to code auditing in three transparent steps.")

    st.markdown(f"""
    <div class="info-card">
        <h4>1. Upload Source Code or Project Repository</h4>
        <p>Submit single source files or a .ZIP project repository. Our scanner identifies supported files (.py, .sql, .dax, .js, .ts, .cpp, .json) and ignores irrelevant build assets.</p>
    </div>
    <div class="info-card">
        <h4>2. One Simple File-Based Rate ({unit_price_display}/file)</h4>
        <p>You only pay for analyzable source files ({unit_price_display} per file). Complete one single Stripe payment for the entire batch with zero subscription lock-in.</p>
    </div>
    <div class="info-card">
        <h4>3. Certified Markdown & PDF Technical Reports</h4>
        <p>Every analyzed file receives its own 7-section canonical Markdown documentation and rendered PDF report. Multi-file uploads include a complete ZIP bundle.</p>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 4. SECURITY & PRIVACY
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
# 5. SIGN IN (PERSONAL & TEAM PORTAL / ADMIN PRICING)
# ==============================================================================
with tab_signin:
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None

    if not st.session_state.auth_user:
        st.subheader("Account Sign In")
        st.caption("Sign in to your personal developer account or your company organization portal.")

        auth_choice = st.radio("Select option:", ["Sign In", "Create Account"], horizontal=True)

        if auth_choice == "Sign In":
            with st.form("form_login"):
                login_email = st.text_input("Email Address")
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

        elif auth_choice == "Create Account":
            with st.form("form_register"):
                acc_type = st.radio(
                    "Account Type:",
                    ["Personal Developer Account", "Company / Organization Account (Team Portal & Shared Billing)"],
                    horizontal=True
                )
                org_name = ""
                if "Organization" in acc_type:
                    org_name = st.text_input("Company / Organization Name", placeholder="Acme Engineering Corp")
                    st.caption("As the organization creator, you will be assigned as the **Company Administrator** with team management and billing access.")
                
                reg_email = st.text_input("Work Email Address")
                reg_pass = st.text_input("Password", type="password")
                btn_reg = st.form_submit_button("Register Account")

                if btn_reg:
                    if reg_email and reg_pass:
                        try:
                            org_id = None
                            if "Organization" in acc_type:
                                if not org_name.strip():
                                    st.warning("Please provide an Organization Name.")
                                    st.stop()
                                new_org = create_organization(name=org_name.strip())
                                org_id = new_org.id

                            new_user = create_user(
                                email=reg_email.strip(),
                                password=reg_pass,
                                organization_id=org_id,
                                role="admin" if org_id else "user"
                            )
                            st.session_state.auth_user = {
                                "id": new_user.id,
                                "email": new_user.email,
                                "organization_id": org_id,
                                "role": new_user.role
                            }
                            st.success(f"Account registered successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Registration failed: {str(e)}")
                    else:
                        st.warning("Please complete all required fields.")

    else:
        user = st.session_state.auth_user
        org = get_organization(user["organization_id"]) if user.get("organization_id") else None

        header_col1, header_col2 = st.columns([3, 1])
        with header_col1:
            if org:
                role_title = "Company Administrator" if user.get("role") == "admin" else "Team Member"
                st.subheader(f"{org.name}")
                st.caption(f"User: **{user['email']}** &nbsp;|&nbsp; Role: **{role_title}**")
            else:
                st.subheader("Personal Account Dashboard")
                st.caption(f"User: **{user['email']}**")
        with header_col2:
            if st.button("Sign Out", key="btn_signout"):
                st.session_state.auth_user = None
                st.rerun()

        st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)

        # ----------------------------------------------------------------------
        # A. COMPANY / ORGANIZATION DASHBOARD
        # ----------------------------------------------------------------------
        if org:
            # 1. Organization Usage & Billing Metrics
            st.subheader("Organization Billing & Audit Usage")
            st.caption("Shared billing metrics and completed team audits.")

            usage = get_org_usage(user["organization_id"])
            u1, u2, u3 = st.columns(3)
            with u1:
                st.metric("Audits Completed", usage["analyses_count"])
            with u2:
                st.metric("Rate Per File", f"${usage['current_price']:.2f} {usage['currency']}")
            with u3:
                st.metric("Total Billed", f"${usage['total_usage_amount']:.2f} {usage['currency']}")

            recent_org_analyses = usage.get("recent_analyses", [])
            if recent_org_analyses:
                st.markdown("<br>", unsafe_allow_html=True)
                st.write("##### Recent Organization Audits & Invoices")
                for item in recent_org_analyses:
                    with st.container():
                        c_date, c_amt, c_status, c_action = st.columns([3, 2, 2, 3])
                        with c_date:
                            st.write(f"**Date:** {item['created_at']}")
                            st.caption(f"Job ID: `{item['id'][:8]}...`")
                        with c_amt:
                            st.write(f"**${item['price']:.2f} {item['currency']}**")
                        with c_status:
                            st.markdown("<span style='color:#2e7d32; font-weight:600;'>Paid & Completed</span>", unsafe_allow_html=True)
                        with c_action:
                            if item.get("report_filename") and os.path.exists(item["report_filename"]):
                                with open(item["report_filename"], "rb") as f_rep:
                                    st.download_button(
                                        label="Download PDF Report",
                                        data=f_rep.read(),
                                        file_name=os.path.basename(item["report_filename"]),
                                        mime="application/pdf",
                                        key=f"dl_org_pdf_{item['id']}"
                                    )
                            else:
                                st.caption("Report archived")
                        st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px dashed #d1c7b7;'>", unsafe_allow_html=True)

            # 2. Team Code Audit Runner
            st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
            st.subheader("Run Team Code Audit")
            st.caption("Submit source code for analysis charged directly to your organization billing account.")

            org_file = st.file_uploader("Upload source file:", type=["py", "sql", "dax", "js", "ts", "cpp", "txt", "json"], key="org_file_upload")
            if org_file:
                file_content = org_file.getvalue().decode("utf-8", errors="ignore")
                if st.button(f"Run Audit on {org_file.name} ({unit_price_display})", type="primary", key="btn_team_audit"):
                    analysis_rec = create_analysis_record(user_id=user["id"], org_id=user["organization_id"], file_count=1, filenames=[org_file.name])
                    with st.spinner("Executing precision code audit..."):
                        charge_res = charge_organization_analysis(org_id=user["organization_id"], analysis_id=analysis_rec.id)
                        if charge_res.get("success"):
                            metrics = CodeAnalyzer.analyze_source_code(file_content, filename=org_file.name)
                            pdf_path = generate_analysis_pdf(analysis_id=analysis_rec.id, analysis_metrics=metrics, price_charged=analysis_rec.price, currency=analysis_rec.currency)
                            update_analysis_status(analysis_rec.id, "completed", report_filename=pdf_path)
                            st.success("Audit complete.")
                            with open(pdf_path, "rb") as f:
                                st.download_button(label="Download PDF Report", data=f.read(), file_name=os.path.basename(pdf_path), mime="application/pdf")
                        else:
                            st.error(f"Payment failed: {charge_res.get('error', 'Card error')}")

            # 3. Company Administrator: Payment Method & Team Members Management
            if user.get("role") == "admin":
                st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
                st.subheader("Corporate Payment Method")
                st.caption("Sync your company card with Stripe so team members can run code audits charged directly to your organization.")

                has_card = bool(org.stripe_customer_id)
                if has_card:
                    st.markdown("<div style='background:#f0fdf4; border:1px solid #86efac; border-radius:8px; padding:12px 16px; margin-bottom:12px; color:#166534;'><b>Active Payment Method Linked</b> — Team audits are charged automatically to your corporate card on file.</div>", unsafe_allow_html=True)
                    btn_card_label = "Update Corporate Card (Stripe)"
                else:
                    st.markdown("<div style='background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding:12px 16px; margin-bottom:12px; color:#92400e;'><b>No Corporate Card Linked</b> — Link a company card via Stripe to enable team code audits.</div>", unsafe_allow_html=True)
                    btn_card_label = "Link Corporate Card (Stripe)"

                if st.button(btn_card_label, key="btn_sync_card", type="primary" if not has_card else "secondary"):
                    app_base_url = os.getenv("APP_URL", "http://localhost:8501")
                    setup_res = setup_organization_billing_session(
                        org_id=org.id,
                        org_name=org.name,
                        success_url=app_base_url,
                        cancel_url=app_base_url
                    )
                    if setup_res.get("mock"):
                        update_organization_stripe(org_id=org.id, stripe_customer_id=f"cus_mock_{org.id}")
                        st.success("Corporate card linked successfully (Demo / Mock Mode)!")
                        st.rerun()
                    elif setup_res.get("url"):
                        st.link_button("Proceed to Stripe to Save Card", setup_res["url"], type="primary")

                st.markdown("<hr class='gold-divider'>", unsafe_allow_html=True)
                st.subheader("Team Management")
                st.caption("Add team members so they can run code audits under your organization.")

                with st.form("form_add_member"):
                    new_email = st.text_input("New Member Work Email")
                    new_pw = st.text_input("Temporary Password", type="password")
                    if st.form_submit_button("Add Team Member & Send Invite") and new_email and new_pw:
                        try:
                            create_user(email=new_email.strip(), password=new_pw, organization_id=user["organization_id"], role="member")
                            
                            # Send automated branded invitation email
                            email_res = send_team_invite_email(
                                to_email=new_email.strip(),
                                org_name=org.name,
                                temp_password=new_pw,
                                inviter_email=user["email"]
                            )
                            if email_res.get("success"):
                                st.success(f"Added member **{new_email}** and sent invitation email via {email_res.get('provider').capitalize()}!")
                            elif email_res.get("reason") == "no_provider":
                                st.success(f"Added member **{new_email}**! (Account created immediately. Add `RESEND_API_KEY` to .env to automate outbound inbox delivery).")
                            else:
                                st.warning(f"Added member **{new_email}**, but email delivery failed: {email_res.get('error')}")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                members = get_org_users(user["organization_id"])
                if members:
                    st.write("##### Active Team Members")
                    for m in members:
                        is_current_user = m["id"] == user["id"]
                        with st.container():
                            c_info, c_role, c_actions = st.columns([3.5, 2, 2.5])
                            with c_info:
                                role_tag = "👑 Administrator" if m["role"] == "admin" else "👤 Member"
                                you_tag = " *(You)*" if is_current_user else ""
                                st.write(f"**{m['email']}**{you_tag}")
                                st.caption(f"Role: {role_tag}")
                            
                            with c_role:
                                if not is_current_user:
                                    role_options = ["member", "admin"]
                                    cur_idx = role_options.index(m["role"]) if m["role"] in role_options else 0
                                    new_role = st.selectbox(
                                        "Role",
                                        options=role_options,
                                        index=cur_idx,
                                        format_func=lambda r: "Admin" if r == "admin" else "Member",
                                        key=f"role_sel_{m['id']}",
                                        label_visibility="collapsed"
                                    )
                                    if new_role != m["role"]:
                                        if update_user_role(m["id"], user["organization_id"], new_role):
                                            st.success(f"Updated {m['email']} to {new_role}")
                                            st.rerun()
                                else:
                                    st.write(f"*{m['role'].capitalize()}*")

                            with c_actions:
                                if not is_current_user:
                                    if st.button("Remove", key=f"btn_rem_{m['id']}", type="secondary"):
                                        if remove_user_from_org(m["id"], user["organization_id"]):
                                            st.success(f"Removed {m['email']} from organization.")
                                            st.rerun()
                                else:
                                    st.caption("Owner Account")

                        st.markdown("<hr style='margin: 0.3rem 0; border: none; border-top: 1px dashed #d1c7b7;'>", unsafe_allow_html=True)

        # ----------------------------------------------------------------------
        # B. PERSONAL ACCOUNT DASHBOARD
        # ----------------------------------------------------------------------
        else:
            st.subheader("Your Billing & Audit History")
            st.caption("Review your completed code quality audits, Stripe payment records, and download previous PDF reports.")

            user_usage = get_user_usage(user["id"])
            u1, u2, u3 = st.columns(3)
            with u1:
                st.metric("Audits Completed", user_usage["analyses_count"])
            with u2:
                st.metric("Standard Rate", f"${user_usage['current_price']:.2f} {user_usage['currency']}")
            with u3:
                st.metric("Total Spent", f"${user_usage['total_usage_amount']:.2f} {user_usage['currency']}")

            recent = user_usage.get("recent_analyses", [])
            if recent:
                st.markdown("<br>", unsafe_allow_html=True)
                st.write("##### Recent Invoices & Audits")
                for item in recent:
                    with st.container():
                        col_date, col_files, col_amt, col_status, col_action = st.columns([2.5, 1.5, 1.5, 2, 2.5])
                        with col_date:
                            st.write(f"**Date:** {item['created_at']}")
                            st.caption(f"Job ID: `{item['id'][:8]}...`")
                        with col_files:
                            st.write(f"**Files:** {item['file_count']}")
                        with col_amt:
                            st.write(f"**${item['price']:.2f} {item['currency']}**")
                        with col_status:
                            if item['status'] == 'completed':
                                st.markdown("<span style='color:#2e7d32; font-weight:600;'>Paid & Completed</span>", unsafe_allow_html=True)
                            elif item['status'] == 'pending_payment':
                                st.markdown("<span style='color:#e65100; font-weight:600;'>Pending Payment</span>", unsafe_allow_html=True)
                            else:
                                st.write(item['status'].capitalize())
                        with col_action:
                            if item.get("report_filename") and os.path.exists(item["report_filename"]):
                                with open(item["report_filename"], "rb") as f_rep:
                                    st.download_button(
                                        label="Download PDF",
                                        data=f_rep.read(),
                                        file_name=os.path.basename(item["report_filename"]),
                                        mime="application/pdf",
                                        key=f"dl_user_pdf_{item['id']}"
                                    )
                            elif item.get("zip_filename") and os.path.exists(item["zip_filename"]):
                                with open(item["zip_filename"], "rb") as f_zip:
                                    st.download_button(
                                        label="Download ZIP",
                                        data=f_zip.read(),
                                        file_name=os.path.basename(item["zip_filename"]),
                                        mime="application/zip",
                                        key=f"dl_user_zip_{item['id']}"
                                    )
                            else:
                                st.caption("No report available")
                        st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px dashed #d1c7b7;'>", unsafe_allow_html=True)
            else:
                st.info("No billing or audit history yet. Upload your source files in the **Analyze Code** tab to run your first audit.")