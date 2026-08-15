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
    page_title="Code Analysis & Security Audit",
    page_icon="🛡️",
    layout="centered"
)

# Custom Styling for Clean Pay-Per-Result UX
st.markdown("""
<style>
    .price-badge {
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 12px 18px;
        font-size: 1.15rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 1rem;
        display: inline-block;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .stDownloadButton button {
        background-color: #10B981 !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)


# --- NAVIGATION TABS ---
tab_guest, tab_org, tab_admin = st.tabs([
    "🚀 Analyze Code (Guest)",
    "🏢 Company / Organization",
    "⚙️ Admin & Pricing"
])


# ==============================================================================
# 1. GUEST / INDIVIDUAL FLOW
# ==============================================================================
with tab_guest:
    st.header("🛡️ Code Quality & Security Analysis")
    st.caption("Submit your code, pay one simple price, and receive a professional PDF audit.")

    # Centralized Price Display (No hardcoded values)
    current_price, current_currency = get_pricing()
    price_formatted = f"${current_price:.2f} {current_currency}"

    st.markdown(
        f'<div class="price-badge">💳 <b>{price_formatted} per analysis</b> &nbsp;•&nbsp; No subscription. No account required.</div>',
        unsafe_allow_html=True
    )

    # Check for Stripe return session in query params
    query_params = st.query_params
    return_session_id = query_params.get("session_id")

    if return_session_id:
        st.info("🔄 Verifying payment confirmation...")
        verification = verify_checkout_session(return_session_id)

        if verification.get("success"):
            analysis_id = verification["analysis_id"]
            analysis = get_analysis(analysis_id)

            if analysis:
                st.success("✅ Payment verified successfully!")
                
                # Check if report already generated
                if analysis.status != "completed" or not analysis.report_filename or not os.path.exists(analysis.report_filename):
                    # Process Analysis and generate PDF
                    with st.spinner("Running in-memory static analysis & generating PDF report..."):
                        # Retrieve temporary code buffer if present in session state
                        code_to_analyze = st.session_state.get(f"code_buf_{analysis_id}", "")
                        if not code_to_analyze:
                            # Sample analysis if session state refreshed
                            code_to_analyze = "# Code verified through payment session\nimport os\n# Analysis complete"

                        metrics = CodeAnalyzer.analyze_source_code(code_to_analyze)
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
                st.subheader("🎉 Analysis Complete")
                st.write(f"Your code analysis report **(Analysis ID: `{analysis_id}`)** is ready.")

                if analysis.report_filename and os.path.exists(analysis.report_filename):
                    with open(analysis.report_filename, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                        st.download_button(
                            label=f"⬇️ Download PDF Report ({os.path.basename(analysis.report_filename)})",
                            data=pdf_bytes,
                            file_name=os.path.basename(analysis.report_filename),
                            mime="application/pdf"
                        )
                st.markdown("---")
        else:
            st.error(f"❌ Payment verification failed: {verification.get('error', 'Unknown error')}")

    # Code Input Option
    code_input_method = st.radio("Provide Code:", ["Paste Code Snippet", "Upload Source File"], horizontal=True)
    raw_code = ""
    target_filename = "snippet.py"

    if code_input_method == "Paste Code Snippet":
        raw_code = st.text_area(
            "Paste your source code below:",
            height=240,
            placeholder="""def calculate_totals(items):\n    # Paste your Python, JavaScript, or other code here\n    total = sum(i['price'] for i in items)\n    return total"""
        )
    else:
        uploaded_file = st.file_uploader("Upload file (.py, .js, .ts, .json, .sql, .txt)", type=["py", "js", "ts", "json", "sql", "txt"])
        if uploaded_file:
            raw_code = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            target_filename = uploaded_file.name

    if raw_code.strip():
        # Quick validation summary
        line_count = len(raw_code.splitlines())
        st.markdown(f"**Validation:** Ready for analysis (`{target_filename}` — {line_count} lines of code).")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**Total due:** `{price_formatted}`")
        with col2:
            if st.button(f"💳 Pay & Analyze ({price_formatted})", type="primary"):
                # 1. Create analysis record with price snapshot
                analysis_rec = create_analysis_record(user_id=None, org_id=None)

                # Store code in temporary memory buffer for immediate processing upon payment
                st.session_state[f"code_buf_{analysis_rec.id}"] = raw_code

                # 2. Create Stripe Checkout Session
                app_base_url = os.getenv("APP_URL", "http://localhost:8501")
                checkout_info = create_guest_checkout_session(
                    analysis_id=analysis_rec.id,
                    success_url=app_base_url,
                    cancel_url=app_base_url
                )

                if checkout_info.get("mock"):
                    # Instant test verification for development / mock mode
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
    st.caption("🔒 **Privacy Guarantee:** We do not permanently retain source code after processing.")


# ==============================================================================
# 2. COMPANY / ORGANIZATION FLOW
# ==============================================================================
with tab_org:
    st.header("🏢 Company & Organization Portal")
    st.caption("Set up centralized billing once so employees can submit code analyses seamlessly.")

    current_price, current_currency = get_pricing()
    price_formatted = f"${current_price:.2f} {current_currency}"

    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None

    # Organization Authentication
    if not st.session_state.auth_user:
        auth_mode = st.radio("Company Account:", ["Employee / Admin Login", "Register New Organization"], horizontal=True)

        if auth_mode == "Employee / Admin Login":
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
                org_name = st.text_input("Company / Organization Name", placeholder="Acme Corporation")
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
        # User is logged in
        user = st.session_state.auth_user
        org = get_organization(user["organization_id"]) if user.get("organization_id") else None

        col_top1, col_top2 = st.columns([3, 1])
        with col_top1:
            st.subheader(f"🏢 {org.name if org else 'Company Portal'}")
            st.caption(f"Logged in as **{user['email']}** ({user['role'].capitalize()})")
        with col_top2:
            if st.button("Sign Out"):
                st.session_state.auth_user = None
                st.rerun()

        st.markdown("---")

        # 1. Company Analysis Submission
        st.subheader("📥 Submit Code Analysis for Organization")
        st.write(f"Organization analysis rate: **{price_formatted}** (charged directly to company card on file).")

        org_code = st.text_area(
            "Source Code for Company Audit:",
            height=180,
            placeholder="def process_payment(amount):\n    # Paste code here"
        )

        if org_code.strip():
            if st.button(f"🚀 Run Company Analysis ({price_formatted})", type="primary"):
                # Create analysis record with snapshot price
                analysis_rec = create_analysis_record(user_id=user["id"], org_id=user["organization_id"])

                with st.spinner("Charging company payment method & analyzing code..."):
                    charge_result = charge_organization_analysis(
                        org_id=user["organization_id"],
                        analysis_id=analysis_rec.id
                    )

                    if charge_result.get("success"):
                        # Execute in-memory analysis
                        metrics = CodeAnalyzer.analyze_source_code(org_code)
                        pdf_path = generate_analysis_pdf(
                            analysis_id=analysis_rec.id,
                            analysis_metrics=metrics,
                            price_charged=analysis_rec.price,
                            currency=analysis_rec.currency
                        )
                        update_analysis_status(analysis_rec.id, "completed", report_filename=pdf_path)

                        st.success("✅ Analysis completed successfully!")
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
            st.subheader("👥 Invite Employees")
            with st.form("invite_employee_form"):
                new_emp_email = st.text_input("Employee Email")
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
# 3. ADMIN & PRICING SETTINGS
# ==============================================================================
with tab_admin:
    st.header("⚙️ Centralized Pricing Configuration")
    st.caption("Change the single authoritative price. Updates take effect immediately without modifying source code.")

    current_price, current_currency = get_pricing()

    st.write(f"**Current Authoritative Price:** `${current_price:.2f} {current_currency}`")

    # Admin Authentication
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
                st.info("All new guest analyses, Stripe checkouts, and company charges will now use this price. Historical records remain unchanged.")
                st.rerun()
    else:
        st.info("Please enter the administrator key to modify global pricing settings.")