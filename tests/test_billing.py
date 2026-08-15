import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from billing_db import (
    init_db,
    close_db,
    get_pricing,
    set_pricing,
    create_organization,
    get_organization,
    create_user,
    authenticate_user,
    create_analysis_record,
    get_analysis,
    update_analysis_status,
    get_org_usage,
    is_event_processed,
    mark_event_processed
)
from stripe_service import (
    create_guest_checkout_session,
    verify_checkout_session,
    charge_organization_analysis
)
from code_analyzer import CodeAnalyzer
from pdf_generator import generate_analysis_pdf


@pytest.fixture(autouse=True)
def setup_test_db():
    """Initializes an isolated in-memory or temp SQLite database for tests."""
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(temp_db_fd)
    db_uri = f"sqlite:///{temp_db_path}"
    init_db(db_uri)

    yield

    close_db()
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except Exception:
            pass


# ==============================================================================
# 1. PRICING & SNAPSHOTTING TESTS
# ==============================================================================

def test_default_pricing_is_fifteen():
    price, currency = get_pricing()
    assert price == 15.00
    assert currency == "USD"


def test_centralized_pricing_update_and_snapshotting():
    # 1. Create analysis at default $15.00
    analysis1 = create_analysis_record()
    assert analysis1.price == 15.00
    assert analysis1.currency == "USD"

    # 2. Update centralized price to $20.00
    set_pricing(20.00, "USD")
    current_price, _ = get_pricing()
    assert current_price == 20.00

    # 3. Create new analysis at $20.00
    analysis2 = create_analysis_record()
    assert analysis2.price == 20.00

    # 4. Verify historical analysis retains original $15.00 price
    fetched_hist = get_analysis(analysis1.id)
    assert fetched_hist.price == 15.00


# ==============================================================================
# 2. GUEST / INDIVIDUAL FLOW TESTS
# ==============================================================================

def test_guest_checkout_and_verification():
    # 1. Create guest analysis
    analysis = create_analysis_record()
    assert analysis.user_id is None
    assert analysis.organization_id is None
    assert analysis.status == "pending_payment"

    # 2. Create Checkout Session
    session_data = create_guest_checkout_session(
        analysis_id=analysis.id,
        success_url="http://localhost:8501",
        cancel_url="http://localhost:8501"
    )
    assert "id" in session_data

    # 3. Server-side payment verification
    verification = verify_checkout_session(session_data["id"])
    assert verification["success"] is True
    assert verification["status"] == "paid"

    # 4. Analysis status in DB is now 'paid'
    updated = get_analysis(analysis.id)
    assert updated.status == "paid"


def test_payment_verification_is_idempotent():
    analysis = create_analysis_record()
    session_data = create_guest_checkout_session(
        analysis_id=analysis.id,
        success_url="http://localhost:8501",
        cancel_url="http://localhost:8501"
    )

    # Call verification multiple times (simulating browser refresh / webhook retries)
    v1 = verify_checkout_session(session_data["id"])
    v2 = verify_checkout_session(session_data["id"])
    v3 = verify_checkout_session(session_data["id"])

    assert v1["success"] is True
    assert v2["success"] is True
    assert v3["success"] is True


# ==============================================================================
# 3. COMPANY / ORGANIZATION TESTS
# ==============================================================================

def test_organization_creation_and_member_authentication():
    org = create_organization(name="Acme Corp")
    assert org.id is not None
    assert org.name == "Acme Corp"

    # Create admin
    user = create_user("admin@acme.com", "secret123", organization_id=org.id, role="admin")
    assert user.id is not None

    # Authenticate
    auth = authenticate_user("admin@acme.com", "secret123")
    assert auth is not None
    assert auth["email"] == "admin@acme.com"
    assert auth["organization_id"] == org.id


def test_company_analysis_and_usage_aggregation():
    org = create_organization(name="Tech Innovators")
    user = create_user("dev@tech.com", "pass123", organization_id=org.id)

    # Submit 2 analyses at $15.00
    a1 = create_analysis_record(user_id=user.id, org_id=org.id)
    charge_organization_analysis(org.id, a1.id)

    a2 = create_analysis_record(user_id=user.id, org_id=org.id)
    charge_organization_analysis(org.id, a2.id)

    # Change price to $20.00
    set_pricing(20.00, "USD")

    # Submit 1 analysis at $20.00
    a3 = create_analysis_record(user_id=user.id, org_id=org.id)
    charge_organization_analysis(org.id, a3.id)

    # Check Usage Aggregation: (2 * $15) + (1 * $20) = $50.00
    usage = get_org_usage(org.id)
    assert usage["analyses_count"] == 3
    assert usage["current_price"] == 20.00
    assert usage["total_usage_amount"] == 50.00


# ==============================================================================
# 4. CODE ANALYSIS & PDF GENERATION TESTS (ZERO CODE RETENTION)
# ==============================================================================

def test_code_analyzer_metrics():
    sample_code = """
import os

def calculate_discount(price, rate):
    \"\"\"Calculates discounted price.\"\"\"
    if rate > 0:
        return price * (1 - rate)
    return price

class Customer:
    def __init__(self, name):
        self.name = name
"""
    metrics = CodeAnalyzer.analyze_source_code(sample_code, "test.py")

    assert metrics["filename"] == "test.py"
    assert metrics["functions_count"] >= 2
    assert metrics["classes_count"] >= 1
    assert metrics["quality_score"] > 50


def test_pdf_generation():
    metrics = CodeAnalyzer.analyze_source_code("def foo():\n    return 42", "foo.py")
    temp_pdf = tempfile.mktemp(suffix=".pdf")

    pdf_path = generate_analysis_pdf(
        analysis_id="test-analysis-1234",
        analysis_metrics=metrics,
        price_charged=15.00,
        currency="USD",
        output_filename=temp_pdf
    )

    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 100  # Valid non-empty PDF document

    # Clean up test artifact
    if os.path.exists(temp_pdf):
        os.remove(temp_pdf)
