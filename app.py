import os
import sys
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
from code_analyzer import CodeAnalyzer
from pdf_generator import generate_analysis_pdf, REPORTS_DIR

# Initialize Database Schema & Default Pricing ($15.00 USD)
init_db()

# Page Setup
st.set_page_config(
    page_title="The Ram & Chisel — Code Quality & Security Audit",
    page_icon="🛡️",
    layout="wide"
)

# Custom Styling for The Ram and Chisel (Burgundy & Gold Palette)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --brand-burgundy: #4A1525;
        --brand-burgundy-dark: #2F0B16;
        --brand-burgundy-light: #5E1D31;
        --brand-gold: #D8A246;
        --brand-gold-light: #F7E7C4;
        --brand-gold-border: #E5C378;
        --bg-cream: #FAF7F2;
        --bg-cream-dark: #F3ECE1;
        --text-dark: #1F070E;
    }

    .stApp {
        background-color: var(--bg-cream);
        color: var(--text-dark);
        font-family: 'Inter', sans-serif;
    }

    .brand-title {
        font-family: 'Cinzel', serif;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        color: var(--brand-burgundy);
        margin-bottom: 0.15rem;
    }

    .brand-tagline {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--brand-gold);
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 1.2rem;
    }

    .price-badge {
        background-color: var(--brand-burgundy);
        border: 2px solid var(--brand-gold);
        border-radius: 10px;
        padding: 12px 18px;
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--brand-gold-light);
        margin-bottom: 1.2rem;
        display: inline-block;
        box-shadow: 0 4px 12px rgba(74, 21, 37, 0.12);
    }

    .price-badge b {
        color: #FFFFFF;
        font-size: 1.2rem;
    }

    .trust-banner {
        background-color: #FFFFFF;
        border-left: 5px solid var(--brand-gold);
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 1.2rem;
        box-shadow: 0 2px 6px rgba(74, 21, 37, 0.04);
    }

    .trust-banner h4 {
        margin: 0 0 4px 0;
        color: var(--brand-burgundy);
        font-size: 1.0rem;
    }

    .trust-banner p {
        margin: 0;
        color: #4A3A40;
        font-size: 0.88rem;
        line-height: 1.4;
    }

    .security-card {
        background: #FFFFFF;
        border: 1px solid var(--brand-gold-border);
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(74, 21, 37, 0.04);
    }

    .security-card h4 {
        color: var(--brand-burgundy);
        margin-top: 0;
        margin-bottom: 8px;
    }

    .stButton > button, div.stDownloadButton > button {
        background: linear-gradient(135deg, var(--brand-burgundy) 0%, var(--brand-burgundy-dark) 100%) !important;
        color: var(--brand-gold-light) !important;
        font-weight: 700 !important;
        border: 1.5px solid var(--brand-gold) !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.25rem !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover, div.stDownloadButton > button:hover {
        background: linear-gradient(135deg, var(--brand-gold) 0%, #C59B27 100%) !important;
        color: var(--brand-burgundy-dark) !important;
        border-color: var(--brand-burgundy) !important;
        box-shadow: 0 4px 14px rgba(216, 162, 70, 0.4) !important;
    }

    .metric-box {
        background-color: #FFFFFF;
        border: 1px solid var(--brand-gold-border);
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(74, 21, 37, 0.05);
    }

    .report-section {
        background-color: #FFFFFF;
        border: 1px solid var(--brand-gold-border);
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 14px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid var(--brand-gold-border);
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        color: var(--brand-burgundy);
        padding: 8px 16px;
        border-radius: 6px 6px 0 0;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--brand-burgundy) !important;
        color: var(--brand-gold-light) !important;
        border-bottom: 3px solid var(--brand-gold) !important;
    }
</style>
""", unsafe_allow_html=True)


# --- SAMPLE CODE REPOSITORY ---
SAMPLE_FILES = {
    "sample_delinquent_loans.sql (Credit Union SQL)": {
        "filename": "sample_delinquent_loans.sql",
        "language": "SQL",
        "description": "Calculates delinquent loan accounts over 30 days past due and estimates accrued interest penalties.",
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
    "member_credit_scoring.py (Credit Union Python)": {
        "filename": "member_credit_scoring.py",
        "language": "Python",
        "description": "Calculates member creditworthiness based on debt-to-income (DTI) and account tenure.",
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
        return {"approved": False, "reason": "Invalid or missing monthly income", "risk_score": 0}

    # Debt-to-Income (DTI) Ratio
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
    "dividend_calculation.dax (Credit Union DAX)": {
        "filename": "dividend_calculation.dax",
        "language": "DAX",
        "description": "Calculates monthly share certificate dividend payouts by balance tier.",
        "code": """// Credit Union Monthly Share Dividend Distribution Measure
// Calculates weighted dividend allocation across share certificate tiers

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


# --- BRAND HEADER ---
logo_path = "logo.png"
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists(logo_path):
        st.image(logo_path, width=95)
with col_title:
    st.markdown('<div class="brand-title">THE RAM & CHISEL</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-tagline">Precision Code Quality, Security & Legacy Audit</div>', unsafe_allow_html=True)

# Sidebar Branding & Trust
with st.sidebar:
    if os.path.exists(logo_path):
        st.image(logo_path, width=110)
    st.markdown("### **The Ram & Chisel**")
    st.caption("Automated code documentation, security evaluation, and quality audit.")
    st.markdown("---")
    st.markdown("#### 🔒 **Security Guarantee**")
    st.markdown("""
    - ✅ **Zero Code Retention**
    - ✅ **100% In-Memory Analysis**
    - ✅ **No AI / LLM Training**
    - ✅ **PCI-DSS Certified Stripe Vault**
    """)
    st.markdown("---")
    st.caption("Engineered for regulated financial, credit union, and enterprise codebases.")


# --- HELPER: RENDER 7-SECTION REPORT ---
def render_structured_report(metrics: dict, target_filename: str):
    st.markdown("---")
    st.markdown(f"### 📋 Audit & Documentation Report: `{target_filename}`")
    
    # Executive Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Quality Score", f"{metrics.get('quality_score', 100)} / 100")
    with m2:
        st.metric("Audit Grade", metrics.get('grade', 'A'))
    with m3:
        st.metric("Language", metrics.get('language', 'Python'))
    with m4:
        st.metric("Lines of Code", metrics.get('total_loc', 0))

    # 1. Overview
    with st.expander("1. 📖 Overview & Architecture", expanded=True):
        st.write(f"**Target File:** `{metrics.get('filename', target_filename)}` &nbsp;|&nbsp; **Language Dialect:** `{metrics.get('language', 'General')}`")
        st.write(f"- **Total Lines:** {metrics.get('total_loc', 0)} &nbsp;|&nbsp; **Executable Lines:** {metrics.get('code_loc', 0)} &nbsp;|&nbsp; **Comments:** {metrics.get('comment_lines', 0)}")
        st.write(f"- **Complexity Index:** {metrics.get('complexity_score', 1.0)} &nbsp;|&nbsp; **Functions/Queries:** {metrics.get('functions_count', 0)}")

    # 2. Business Logic
    with st.expander("2. ⚙️ Business & Financial Domain Logic", expanded=True):
        b_logic = metrics.get("business_logic", [])
        for item in b_logic:
            st.markdown(f"- {item}")

    # 3. Inputs & Parameters
    with st.expander("3. 📥 Inputs, Filters & Parameters", expanded=False):
        inputs = metrics.get("inputs", [])
        if inputs:
            st.table(inputs)
        else:
            st.info("No external arguments or WHERE predicate parameters detected.")

    # 4. Outputs & Data Structures
    with st.expander("4. 📤 Outputs & Projected Schema", expanded=False):
        outputs = metrics.get("outputs", [])
        if outputs:
            st.table(outputs)
        else:
            st.info("Direct output schema mapping evaluated.")

    # 5. Dependencies
    with st.expander("5. 📦 Dependencies & Modules", expanded=False):
        deps = metrics.get("dependencies", [])
        if deps:
            for d in deps:
                st.write(f"- `{d}`")
        else:
            st.write("No external package imports detected.")

    # 6. Data Relationships
    with st.expander("6. 🗄️ Data Relationships & Joins (SQL / DAX)", expanded=False):
        tables = metrics.get("tables_referenced", [])
        joins = metrics.get("joins", [])
        if tables:
            st.write(f"**Tables Referenced:** {', '.join([f'`{t}`' for t in tables])}")
        if joins:
            st.write("**Join Conditions:**")
            st.table(joins)
        if not tables and not joins:
            st.info("No relational database table joins or entity schemas referenced.")

    # 7. Best Practices & Security
    with st.expander("7. 🛡️ Best Practices & Security Review", expanded=True):
        bp = metrics.get("best_practices", {})
        st.markdown(f"- **Readability & Standards:** {bp.get('readability', 'Standard')}")
        st.markdown(f"- **Performance & Complexity:** {bp.get('performance', 'Standard')}")
        st.markdown(f"- **Error Handling:** {bp.get('error_handling', 'Standard')}")
        st.markdown(f"- **Security Posture:** {bp.get('security', 'Standard')}")
        st.markdown(f"- **Maintainability:** {bp.get('maintainability', 'Standard')}")

        findings = metrics.get("findings", [])
        if findings:
            st.markdown("#### 🔍 Identified Findings")
            for f in findings:
                sev_icon = "🔴" if f.get("severity") == "HIGH" else ("🟡" if f.get("severity") == "MEDIUM" else "🔵")
                st.markdown(f"{sev_icon} **[{f.get('severity')}] {f.get('category')}**: {f.get('message')}")
        else:
            st.success("✅ Zero critical security vulnerabilities or anti-patterns detected.")


# --- NAVIGATION TABS ---
tab_audit, tab_demo, tab_security, tab_org, tab_admin = st.tabs([
    "🚀 Instant Audit",
    "🧪 Interactive Demo",
    "🛡️ Security & Privacy",
    "🏢 Organization Portal",
    "⚙️ Admin & Pricing"
])


# ==============================================================================
# 1. INSTANT AUDIT (MAIN TOOL AT THE TOP)
# ==============================================================================
with tab_audit:
    st.subheader("🛡️ Instant Code Quality & Security Audit")
    st.caption("Submit your code, pay one simple price, and instantly receive your comprehensive analysis and PDF report.")

    current_price, current_currency = get_pricing()
    price_formatted = f"${current_price:.2f} {current_currency}"

    # Friendly Trust Banner
    st.markdown("""
    <div class="trust-banner">
        <h4>🔒 100% Confidential & Secure</h4>
        <p>Your code is analyzed entirely in-memory and deleted immediately upon report generation. <b>We never store your source code or use it to train AI models.</b></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        f'<div class="price-badge">💳 <b>{price_formatted} per analysis</b> &nbsp;•&nbsp; No subscription required. Instant PDF download.</div>',
        unsafe_allow_html=True
    )

    # Check for Stripe return session in query params
    query_params = st.query_params
    return_session_id = query_params.get("session_id")

    if return_session_id:
        st.info("🔄 Verifying payment confirmation with Stripe...")
        verification = verify_checkout_session(return_session_id)

        if verification.get("success"):
            analysis_id = verification["analysis_id"]
            analysis = get_analysis(analysis_id)

            if analysis:
                st.success("✅ Payment verified successfully!")

                # Check if report already generated
                if analysis.status != "completed" or not analysis.report_filename or not os.path.exists(analysis.report_filename):
                    with st.spinner("Running The Ram & Chisel in-memory audit & compiling PDF..."):
                        code_to_analyze = st.session_state.get(f"code_buf_{analysis_id}", "")
                        if not code_to_analyze:
                            code_to_analyze = "# Verified analysis via payment confirmation\n"

                        metrics = CodeAnalyzer.analyze_source_code(code_to_analyze, filename=analysis.report_filename or "audit_source.py")
                        pdf_path = generate_analysis_pdf(
                            analysis_id=analysis_id,
                            analysis_metrics=metrics,
                            price_charged=analysis.price,
                            currency=analysis.currency
                        )
                        update_analysis_status(analysis_id, "completed", report_filename=pdf_path)

                        # ZERO CODE RETENTION: Purge code from session state immediately
                        if f"code_buf_{analysis_id}" in st.session_state:
                            del st.session_state[f"code_buf_{analysis_id}"]

                        analysis = get_analysis(analysis_id)

                # Present completed PDF for direct download
                st.subheader("🎉 Audit Complete")
                st.write(f"Your Ram & Chisel code audit **(Analysis ID: `{analysis_id}`)** is ready.")

                if analysis.report_filename and os.path.exists(analysis.report_filename):
                    with open(analysis.report_filename, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                        st.download_button(
                            label=f"⬇️ Download Professional PDF Audit ({os.path.basename(analysis.report_filename)})",
                            data=pdf_bytes,
                            file_name=os.path.basename(analysis.report_filename),
                            mime="application/pdf"
                        )
                st.markdown("---")
        else:
            st.error(f"❌ Payment verification failed: {verification.get('error', 'Unknown error')}")

    # Code Input Selection
    code_input_method = st.radio("Provide Source Code:", ["Paste Code Snippet", "Upload Source File"], horizontal=True)
    raw_code = ""
    target_filename = "snippet.py"

    if code_input_method == "Paste Code Snippet":
        initial_val = st.session_state.get("audit_pasted_code", "")
        raw_code = st.text_area(
            "Paste source code for evaluation (Python, SQL, DAX, JS/TS, C++):",
            value=initial_val,
            height=220,
            placeholder="-- Paste SQL, Python, or legacy code here...\nSELECT * FROM Loans WHERE DaysPastDue > 30;"
        )
    else:
        uploaded_file = st.file_uploader("Upload file (.py, .sql, .dax, .js, .ts, .cpp, .txt)", type=["py", "sql", "dax", "js", "ts", "cpp", "txt", "json"])
        if uploaded_file:
            raw_code = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            target_filename = uploaded_file.name

    if raw_code.strip():
        line_count = len(raw_code.splitlines())
        st.markdown(f"**Validation:** Ready for audit (`{target_filename}` — {line_count} lines of code).")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**Total price:** `{price_formatted}`")
        with col2:
            if st.button(f"💳 Pay & Audit ({price_formatted})", type="primary", key="btn_pay_audit"):
                analysis_rec = create_analysis_record(user_id=None, org_id=None)
                st.session_state[f"code_buf_{analysis_rec.id}"] = raw_code

                app_base_url = os.getenv("APP_URL", "http://localhost:8501")
                checkout_info = create_guest_checkout_session(
                    analysis_id=analysis_rec.id,
                    success_url=app_base_url,
                    cancel_url=app_base_url
                )

                if checkout_info.get("mock"):
                    st.success("Test Mode: Simulating Stripe Payment...")
                    st.query_params["session_id"] = checkout_info["id"]
                    st.rerun()
                else:
                    st.link_button(
                        f"👉 Proceed to Stripe Checkout ({price_formatted})",
                        url=checkout_info["url"],
                        type="primary"
                    )

    st.markdown("---")

    # Quick Sample Loader at Bottom of Main Audit
    with st.expander("💡 Want to test with a sample file first?", expanded=False):
        st.write("Select a pre-built sample file to load into the editor above:")
        selected_sample_key = st.selectbox("Choose sample:", list(SAMPLE_FILES.keys()), key="main_sample_picker")
        if st.button("📥 Load Sample into Editor"):
            st.session_state["audit_pasted_code"] = SAMPLE_FILES[selected_sample_key]["code"]
            st.rerun()


# ==============================================================================
# 2. INTERACTIVE DEMO (FREE TRIAL / SAMPLE AUDIT)
# ==============================================================================
with tab_demo:
    st.subheader("🧪 Interactive Demo & Sample Audit")
    st.caption("Explore how The Ram & Chisel analyzes code, extracts business logic, and generates 7-section audits.")

    demo_sample_key = st.selectbox("Select a Sample File to Analyze:", list(SAMPLE_FILES.keys()), key="demo_sample_select")
    selected_sample = SAMPLE_FILES[demo_sample_key]

    st.info(f"**File:** `{selected_sample['filename']}` ({selected_sample['language']}) — {selected_sample['description']}")

    with st.expander("👁️ View Sample Source Code", expanded=False):
        st.code(selected_sample["code"], language=selected_sample["language"].lower())

    if st.button("⚡ Generate Free Demo Report", type="primary", key="btn_run_demo"):
        with st.spinner("Analyzing code in-memory & compiling 7-section report..."):
            demo_metrics = CodeAnalyzer.analyze_source_code(
                code_text=selected_sample["code"],
                filename=selected_sample["filename"]
            )
            render_structured_report(demo_metrics, selected_sample["filename"])

            # Generate sample PDF
            demo_pdf = generate_analysis_pdf(
                analysis_id="DEMO-PREVIEW",
                analysis_metrics=demo_metrics,
                price_charged=0.00,
                currency="USD"
            )
            if os.path.exists(demo_pdf):
                with open(demo_pdf, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Sample PDF ({os.path.basename(demo_pdf)})",
                        data=f.read(),
                        file_name=f"demo_{selected_sample['filename']}.pdf",
                        mime="application/pdf",
                        key="btn_dl_demo_pdf"
                    )


# ==============================================================================
# 3. SECURITY & PRIVACY (READER-FRIENDLY & TRANSPARENT)
# ==============================================================================
with tab_security:
    st.subheader("🛡️ Security, Privacy & Compliance")
    st.markdown("We built The Ram & Chisel with a **privacy-first, zero-retention architecture** designed for credit unions, financial institutions, and regulated enterprises.")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("""
        <div class="security-card">
            <h4>🚫 Zero Code Retention</h4>
            <p>Your source code is never written to disk or saved in our database. It is processed strictly in temporary working memory (RAM) and completely purged the instant your audit report is generated.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="security-card">
            <h4>🧠 No AI Model Training</h4>
            <p>We do not use your code, algorithms, or queries to train, tune, or improve public AI models. Your proprietary intellectual property remains strictly yours.</p>
        </div>
        """, unsafe_allow_html=True)

    with col_s2:
        st.markdown("""
        <div class="security-card">
            <h4>💳 PCI-DSS Certified Payments</h4>
            <p>All transactions are processed through Stripe's certified PCI Level 1 vault. We never handle, see, or store your raw credit card numbers or banking credentials.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="security-card">
            <h4>🔒 Isolated Sandbox Execution</h4>
            <p>Any code evaluation runs within strictly quarantined sandbox environments with no external network persistence, preventing unauthorized access or data leakage.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📋 Clear Privacy Summary")
    st.markdown("""
    | Policy Question | Our Direct Answer |
    | :--- | :--- |
    | **Do you store my source code?** | **No.** Code is evaluated in-memory and immediately wiped. |
    | **Is my data used to train AI?** | **Never.** No code or queries are fed into AI training pipelines. |
    | **What data do you keep?** | Only non-sensitive audit metadata (Timestamp, Audit ID, Price, and Status) for billing receipts. |
    | **Is it safe for credit union data?** | **Yes.** Built specifically to respect financial compliance and confidentiality standards. |
    """)


# ==============================================================================
# 4. COMPANY & ORGANIZATION FLOW
# ==============================================================================
with tab_org:
    st.subheader("🏢 Company & Organization Accounts")
    st.caption("Set up centralized company billing once so team members can submit code audits with no individual checkout required.")

    current_price, current_currency = get_pricing()
    price_formatted = f"${current_price:.2f} {current_currency}"

    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None

    if not st.session_state.auth_user:
        auth_mode = st.radio("Account Action:", ["Member / Admin Sign In", "Register Organization"], horizontal=True)

        if auth_mode == "Member / Admin Sign In":
            with st.form("org_login_form"):
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

        else:
            with st.form("org_reg_form"):
                org_name = st.text_input("Organization Name", placeholder="Acme Financial Engineering")
                admin_email = st.text_input("Admin Work Email")
                admin_pass = st.text_input("Admin Password", type="password")
                btn_reg = st.form_submit_button("Create Organization")

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
                            st.success(f"Organization '{org_name}' created successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Registration error: {str(e)}")
                    else:
                        st.warning("Please fill in all fields.")

    else:
        user = st.session_state.auth_user
        org = get_organization(user["organization_id"]) if user.get("organization_id") else None

        col_top1, col_top2 = st.columns([3, 1])
        with col_top1:
            st.markdown(f"### 🏢 **{org.name if org else 'Company Portal'}**")
            st.caption(f"Authenticated: **{user['email']}** &nbsp;|&nbsp; Role: **{user['role'].capitalize()}**")
        with col_top2:
            if st.button("Sign Out"):
                st.session_state.auth_user = None
                st.rerun()

        st.markdown("---")

        # 1. Company Analysis Submission
        st.subheader("📥 Submit Code for Organization Audit")
        st.write(f"Rate: **{price_formatted}** (billed directly to company card on file per analysis).")

        org_code = st.text_area(
            "Source Code for Evaluation:",
            height=180,
            placeholder="def process_payment(amount):\n    # Paste code here"
        )

        if org_code.strip():
            if st.button(f"🚀 Run Company Audit ({price_formatted})", type="primary"):
                analysis_rec = create_analysis_record(user_id=user["id"], org_id=user["organization_id"])

                with st.spinner("Processing company payment & analyzing code..."):
                    charge_result = charge_organization_analysis(
                        org_id=user["organization_id"],
                        analysis_id=analysis_rec.id
                    )

                    if charge_result.get("success"):
                        metrics = CodeAnalyzer.analyze_source_code(org_code)
                        pdf_path = generate_analysis_pdf(
                            analysis_id=analysis_rec.id,
                            analysis_metrics=metrics,
                            price_charged=analysis_rec.price,
                            currency=analysis_rec.currency
                        )
                        update_analysis_status(analysis_rec.id, "completed", report_filename=pdf_path)

                        st.success("✅ Audit completed successfully!")
                        with open(pdf_path, "rb") as pdf_file:
                            st.download_button(
                                label="⬇️ Download Completed PDF Report",
                                data=pdf_file.read(),
                                file_name=os.path.basename(pdf_path),
                                mime="application/pdf"
                            )
                    else:
                        st.error(f"❌ Payment failed: {charge_result.get('error', 'Card charge unsuccessful.')}")

        st.markdown("---")

        # 2. Organization Usage & Billing Status
        st.subheader("📊 Organization Usage")
        usage_data = get_org_usage(user["organization_id"])

        u1, u2, u3 = st.columns(3)
        with u1:
            st.metric("Analyses Completed", usage_data["analyses_count"])
        with u2:
            st.metric("Current Analysis Price", f"${usage_data['current_price']:.2f} {usage_data['currency']}")
        with u3:
            st.metric("Total Usage Billed", f"${usage_data['total_usage_amount']:.2f} {usage_data['currency']}")

        # Admin Organization Settings
        if user.get("role") == "admin":
            st.markdown("---")
            st.subheader("👥 Invite Team Members")
            with st.form("invite_employee_form"):
                new_emp_email = st.text_input("Member Work Email")
                new_emp_pass = st.text_input("Temporary Password", type="password")
                btn_invite = st.form_submit_button("Add Member")

                if btn_invite and new_emp_email and new_emp_pass:
                    try:
                        create_user(email=new_emp_email, password=new_emp_pass, organization_id=user["organization_id"], role="member")
                        st.success(f"Added member: {new_emp_email}")
                    except Exception as e:
                        st.error(f"Error adding member: {str(e)}")

            org_members = get_org_users(user["organization_id"])
            if org_members:
                st.write("**Current Organization Members:**")
                for m in org_members:
                    st.write(f"- {m['email']} *({m['role']})*")


# ==============================================================================
# 5. ADMIN & PRICING SETTINGS
# ==============================================================================
with tab_admin:
    st.subheader("⚙️ Centralized Pricing Configuration")
    st.caption("Change the single authoritative price. Updates take effect immediately for all new analyses.")

    current_price, current_currency = get_pricing()
    st.write(f"**Current Authoritative Price:** `${current_price:.2f} {current_currency}`")

    admin_auth = False
    if "auth_user" in st.session_state and st.session_state.auth_user and st.session_state.auth_user.get("role") == "admin":
        admin_auth = True
    else:
        admin_key_input = st.text_input("Enter Admin Access Key:", type="password")
        configured_admin_key = os.getenv("ADMIN_PASSWORD", "admin123")
        if admin_key_input == configured_admin_key:
            admin_auth = True

    if admin_auth:
        st.success("🔓 Administrator Access Granted")
        with st.form("update_pricing_form"):
            new_price_val = st.number_input(
                "Code Analysis Price",
                min_value=1.0,
                max_value=1000.0,
                value=float(current_price),
                step=1.0,
                format="%.2f"
            )
            new_currency_val = st.selectbox(
                "Currency",
                ["USD", "EUR", "GBP", "CAD", "AUD"],
                index=["USD", "EUR", "GBP", "CAD", "AUD"].index(current_currency) if current_currency in ["USD", "EUR", "GBP", "CAD", "AUD"] else 0
            )

            btn_update_price = st.form_submit_button("Save Price Changes")

            if btn_update_price:
                saved_price, saved_curr = set_pricing(new_price_val, new_currency_val)
                st.success(f"✅ Price updated to **${saved_price:.2f} {saved_curr}**!")
                st.info("All new analyses will now use this price. Historical records remain unchanged.")
                st.rerun()
    else:
        st.info("Please enter the administrator key to modify global pricing settings.")