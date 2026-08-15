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

# Initialize Database Schema & Default Pricing
init_db()

# Page Setup - Centered for focus and elegance
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
        gap: 14px;
        margin-bottom: 2rem;
        padding-top: 0.5rem;
    }

    .brand-logo-text {
        font-family: 'Cinzel', serif;
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        color: var(--brand-burgundy);
        line-height: 1.1;
    }

    /* Hero Section */
    .hero-container {
        text-align: center;
        padding: 1.5rem 0 2rem 0;
    }

    .hero-title {
        font-family: 'Cinzel', serif;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        color: var(--brand-burgundy);
        margin-bottom: 0.5rem;
        line-height: 1.2;
    }

    .hero-subtitle {
        font-size: 1.1rem;
        color: var(--text-muted);
        margin-bottom: 1.4rem;
        font-weight: 400;
    }

    .hero-price {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--brand-burgundy);
        margin-bottom: 0.2rem;
    }

    .hero-price-sub {
        font-size: 0.92rem;
        color: var(--brand-gold);
        font-weight: 600;
        letter-spacing: 0.04em;
        margin-bottom: 1.8rem;
    }

    /* Privacy line */
    .privacy-notice {
        text-align: center;
        color: var(--text-muted);
        font-size: 0.88rem;
        margin-top: 1rem;
        margin-bottom: 1.4rem;
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
        padding: 20px;
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

    /* Hide standard Streamlit header decoration to keep focus */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- SAMPLE CODE ASSETS FOR HOW IT WORKS / PREVIEWS ---
SAMPLE_FILES = {
    "Credit Union Delinquency Query (SQL)": {
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
    "Member Risk & Credit Scoring (Python)": {
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
    "Monthly Dividend Calculation (DAX)": {
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


# --- CLEAN COMPACT BRAND HEADER ---
logo_path = "logo.png"
col_logo_left, col_logo_right = st.columns([1, 7])
with col_logo_left:
    if os.path.exists(logo_path):
        st.image(logo_path, width=64)
with col_logo_right:
    st.markdown('<div class="brand-logo-text" style="padding-top: 12px;">THE RAM & CHISEL</div>', unsafe_allow_html=True)


# --- DYNAMIC PRICING RETRIEVAL ---
current_price, current_currency = get_pricing()
price_display = f"${current_price:.2f} {current_currency}" if current_currency != "USD" else f"${current_price:.0f}" if current_price.is_integer() else f"${current_price:.2f}"


# --- SIMPLIFIED MAIN NAVIGATION ---
tab_analyze, tab_how, tab_security, tab_signin = st.tabs([
    "Analyze",
    "How It Works",
    "Security",
    "Sign In"
])


# ==============================================================================
# 1. ANALYZE (PRIMARY DESTINATION & WORKFLOW)
# ==============================================================================
with tab_analyze:
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">Code Quality & Security Audit</div>
        <div class="hero-subtitle">Upload your code. Get a professional analysis and PDF report.</div>
        <div class="hero-price">{price_display} per analysis</div>
        <div class="hero-price-sub">NO SUBSCRIPTION. NO ACCOUNT REQUIRED.</div>
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
                st.success("Payment verified successfully.")

                if analysis.status != "completed" or not analysis.report_filename or not os.path.exists(analysis.report_filename):
                    with st.spinner("Generating code analysis & compiling PDF report..."):
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

                        # ZERO CODE RETENTION: Purge code from memory buffer immediately
                        if f"code_buf_{analysis_id}" in st.session_state:
                            del st.session_state[f"code_buf_{analysis_id}"]

                        analysis = get_analysis(analysis_id)

                st.subheader("Your Analysis is Complete")
                st.write(f"Report ID: `{analysis_id}`")

                if analysis.report_filename and os.path.exists(analysis.report_filename):
                    with open(analysis.report_filename, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                        st.download_button(
                            label=f"⬇️ Download PDF Analysis ({os.path.basename(analysis.report_filename)})",
                            data=pdf_bytes,
                            file_name=os.path.basename(analysis.report_filename),
                            mime="application/pdf",
                            key="btn_download_completed_pdf"
                        )
                st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.error(f"Payment verification issue: {verification.get('error', 'Unable to verify session.')}")

    # Primary Upload Interaction
    input_mode = st.radio("Input method:", ["Upload Files", "Paste Snippet"], horizontal=True, label_visibility="collapsed")
    raw_code = ""
    target_filename = "snippet.py"

    if input_mode == "Upload Files":
        uploaded_file = st.file_uploader(
            "Upload your code",
            type=["py", "sql", "dax", "js", "ts", "cpp", "txt", "json"],
            help="Supported formats: PY, SQL, DAX, JS, TS, CPP, TXT, JSON"
        )
        if uploaded_file:
            raw_code = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            target_filename = uploaded_file.name
    else:
        pasted_text = st.session_state.get("quick_loaded_code", "")
        raw_code = st.text_area(
            "Paste source code for analysis:",
            value=pasted_text,
            height=200,
            placeholder="Paste Python, SQL, DAX, JavaScript, or C++ code here..."
        )

    # Privacy guarantee line
    st.markdown('<div class="privacy-notice">🔒 <b>Private by design</b> — source code isn\'t retained after analysis.</div>', unsafe_allow_html=True)

    # Primary Action CTA
    if raw_code.strip():
        line_count = len(raw_code.splitlines())
        st.caption(f"Ready: `{target_filename}` ({line_count} lines)")

        if st.button(f"Analyze My Code — {price_display}", type="primary", key="btn_primary_analyze"):
            analysis_rec = create_analysis_record(user_id=None, org_id=None)
            st.session_state[f"code_buf_{analysis_rec.id}"] = raw_code

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
                    f"👉 Continue to Stripe Checkout ({price_display})",
                    url=checkout_info["url"],
                    type="primary"
                )
    else:
        st.button(f"Analyze My Code — {price_display}", disabled=True, key="btn_disabled_analyze")

    # Secondary Sample Trigger (Non-competing, subtle)
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Want to see an example first?", expanded=False):
        st.write("Load a sample credit union file to test the workflow:")
        sample_choice = st.selectbox("Choose sample file:", list(SAMPLE_FILES.keys()), key="select_inline_sample")
        if st.button("Load into editor", key="btn_load_inline_sample"):
            st.session_state["quick_loaded_code"] = SAMPLE_FILES[sample_choice]["code"]
            st.rerun()


# ==============================================================================
# 2. HOW IT WORKS
# ==============================================================================
with tab_how:
    st.subheader("How The Ram & Chisel Works")
    st.write("A direct, three-step process to audit your source code without friction or subscriptions.")

    st.markdown("""
    <div class="info-card">
        <h4>1. Upload Code</h4>
        <p>Submit a source file (.py, .sql, .dax, .js, .ts, .cpp, .txt) or paste a snippet directly into the analyzer.</p>
    </div>
    <div class="info-card">
        <h4>2. Pay One Simple Price</h4>
        <p>Complete a secure one-time payment via Stripe. No ongoing commitments or subscription locks.</p>
    </div>
    <div class="info-card">
        <h4>3. Receive Professional PDF Report</h4>
        <p>Our static engine analyzes syntax, complexity, security patterns, and maintainability in memory, delivering a downloadable PDF audit.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Sample Analysis Preview")
    st.write("Explore an example report generated by our static analysis engine.")

    preview_sample_key = st.selectbox("Select example:", list(SAMPLE_FILES.keys()), key="select_preview_sample")
    preview_sample = SAMPLE_FILES[preview_sample_key]

    with st.expander("View sample source code", expanded=False):
        st.code(preview_sample["code"], language=preview_sample["language"].lower())

    if st.button("Generate Preview Report", key="btn_run_preview"):
        with st.spinner("Generating sample metrics..."):
            preview_metrics = CodeAnalyzer.analyze_source_code(
                code_text=preview_sample["code"],
                filename=preview_sample["filename"]
            )
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Quality Score", f"{preview_metrics.get('quality_score', 100)} / 100")
            with c2:
                st.metric("Audit Grade", preview_metrics.get('grade', 'A'))
            with c3:
                st.metric("Lines of Code", preview_metrics.get('total_loc', 0))

            preview_pdf = generate_analysis_pdf(
                analysis_id="SAMPLE-PREVIEW",
                analysis_metrics=preview_metrics,
                price_charged=0.00,
                currency="USD"
            )
            if os.path.exists(preview_pdf):
                with open(preview_pdf, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Sample PDF",
                        data=f.read(),
                        file_name=f"sample_{preview_sample['filename']}.pdf",
                        mime="application/pdf",
                        key="btn_dl_sample_preview_pdf"
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
        <h4>Minimal Metadata Retention</h4>
        <p>Our database retains only non-sensitive transactional records (transaction timestamp, analysis identifier, price paid, and fulfillment status) for customer receipt and accounting verification.</p>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 4. SIGN IN & ORGANIZATION PORTAL / ADMIN
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
        # Authenticated Session View
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
            st.subheader("Centralized Pricing Configuration")
            st.caption("Update the single authoritative price for all subsequent code analyses.")

            curr_price, curr_currency = get_pricing()
            st.write(f"Current System Price: **${curr_price:.2f} {curr_currency}**")

            with st.form("form_update_pricing"):
                new_price = st.number_input("Analysis Price", min_value=1.0, max_value=1000.0, value=float(curr_price), step=1.0, format="%.2f")
                new_curr = st.selectbox("Currency", ["USD", "EUR", "GBP", "CAD", "AUD"], index=["USD", "EUR", "GBP", "CAD", "AUD"].index(curr_currency) if curr_currency in ["USD", "EUR", "GBP", "CAD", "AUD"] else 0)
                btn_save_price = st.form_submit_button("Update Global Price")

                if btn_save_price:
                    p, c = set_pricing(new_price, new_curr)
                    st.success(f"Price updated to **${p:.2f} {c}** across the application.")
                    st.rerun()

        # Organization Team Portal Features
        if user.get("organization_id"):
            st.markdown("---")
            st.subheader("Submit Code for Team Audit")
            org_code = st.text_area("Source code:", height=160, placeholder="Paste team code here...")

            if org_code.strip():
                if st.button(f"Run Team Audit ({price_display})", type="primary", key="btn_team_audit"):
                    analysis_rec = create_analysis_record(user_id=user["id"], org_id=user["organization_id"])
                    with st.spinner("Processing analysis..."):
                        charge_res = charge_organization_analysis(org_id=user["organization_id"], analysis_id=analysis_rec.id)
                        if charge_res.get("success"):
                            metrics = CodeAnalyzer.analyze_source_code(org_code)
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
                st.metric("Analyses Completed", usage["analyses_count"])
            with u2:
                st.metric("Rate Per Analysis", f"${usage['current_price']:.2f} {usage['currency']}")
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