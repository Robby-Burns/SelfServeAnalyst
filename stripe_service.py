import os
from typing import Dict, Any, Optional

try:
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
except ImportError:
    stripe = None

from billing_db import (
    get_pricing,
    get_analysis,
    update_analysis_status,
    get_organization,
    is_event_processed,
    mark_event_processed
)


def is_stripe_configured() -> bool:
    """Returns True if a live or test Stripe API key is present."""
    if stripe is None:
        return False
    key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    return bool(key and not key.startswith("your_") and not key.startswith("mock_"))


def create_guest_checkout_session(
    analysis_id: str,
    success_url: str,
    cancel_url: str
) -> Dict[str, Any]:
    """
    Creates a Stripe Checkout Session for a one-off analysis using the centrally snapshotted price.
    """
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise ValueError(f"Analysis with ID {analysis_id} not found.")

    price_in_cents = int(round(analysis.price * 100))
    currency = analysis.currency.lower()

    if not is_stripe_configured():
        # Demo / Test Mock Mode
        mock_session_id = f"cs_test_mock_{analysis_id}"
        update_analysis_status(
            analysis_id=analysis_id,
            status="pending_payment",
            stripe_checkout_session_id=mock_session_id
        )
        return {
            "id": mock_session_id,
            "url": f"{success_url}?session_id={mock_session_id}",
            "mock": True
        }

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": "Code Analysis & PDF Report",
                        "description": f"Comprehensive code quality, security, and complexity analysis (Analysis ID: {analysis_id})",
                    },
                    "unit_amount": price_in_cents,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        metadata={
            "analysis_id": analysis_id,
            "type": "guest_analysis"
        },
        success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=cancel_url,
    )

    update_analysis_status(
        analysis_id=analysis_id,
        status="pending_payment",
        stripe_checkout_session_id=session.id
    )

    return {
        "id": session.id,
        "url": session.url,
        "mock": False
    }


def verify_checkout_session(session_id: str) -> Dict[str, Any]:
    """
    Server-side verification of a Stripe Checkout Session.
    Ensures payment is truly paid before transitioning state to 'paid'.
    Idempotent: Duplicate calls will safely return verified state without duplicate side-effects.
    """
    # Handle mock mode
    if session_id.startswith("cs_test_mock_"):
        analysis_id = session_id.replace("cs_test_mock_", "")
        analysis = get_analysis(analysis_id)
        if not analysis:
            return {"success": False, "error": "Analysis not found"}
        if analysis.status in ["paid", "processing", "completed"]:
            return {"success": True, "analysis_id": analysis_id, "status": analysis.status}
        update_analysis_status(analysis_id, "paid", stripe_checkout_session_id=session_id)
        return {"success": True, "analysis_id": analysis_id, "status": "paid"}

    if not is_stripe_configured():
        return {"success": False, "error": "Stripe API key is not configured."}

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        analysis_id = session.metadata.get("analysis_id")
        if not analysis_id:
            return {"success": False, "error": "Missing analysis_id in session metadata"}

        analysis = get_analysis(analysis_id)
        if not analysis:
            return {"success": False, "error": f"Analysis {analysis_id} not found"}

        # If already paid or completed, return success idempotently
        if analysis.status in ["paid", "processing", "completed"]:
            return {"success": True, "analysis_id": analysis_id, "status": analysis.status}

        if session.payment_status == "paid":
            # Idempotency event check
            event_id = f"checkout_paid_{session.id}"
            if not is_event_processed(event_id):
                mark_event_processed(event_id, "checkout.session.completed")

            update_analysis_status(
                analysis_id=analysis_id,
                status="paid",
                stripe_payment_intent_id=str(session.payment_intent) if session.payment_intent else None,
                stripe_checkout_session_id=session.id
            )
            return {"success": True, "analysis_id": analysis_id, "status": "paid"}
        else:
            update_analysis_status(analysis_id, "payment_failed")
            return {"success": False, "error": f"Payment status: {session.payment_status}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def setup_organization_billing_session(
    org_id: str,
    org_name: str,
    success_url: str,
    cancel_url: str
) -> Dict[str, Any]:
    """
    Creates a Stripe Setup Checkout Session for an organization to save a payment method
    for future per-analysis off-session charges.
    """
    if not is_stripe_configured():
        # Mock mode
        mock_session_id = f"seti_mock_{org_id}"
        return {
            "id": mock_session_id,
            "url": f"{success_url}?setup_session_id={mock_session_id}",
            "mock": True
        }

    org = get_organization(org_id)
    customer_id = org.stripe_customer_id if org else None

    if not customer_id:
        customer = stripe.Customer.create(
            name=org_name,
            metadata={"org_id": org_id}
        )
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="setup",
        customer=customer_id,
        metadata={"org_id": org_id, "type": "org_setup"},
        success_url=f"{success_url}?setup_session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=cancel_url
    )

    return {
        "id": session.id,
        "url": session.url,
        "customer_id": customer_id,
        "mock": False
    }


def charge_organization_analysis(org_id: str, analysis_id: str) -> Dict[str, Any]:
    """
    Charges the organization's saved payment method on file per completed analysis.
    Uses off-session PaymentIntent.
    """
    analysis = get_analysis(analysis_id)
    if not analysis:
        return {"success": False, "error": "Analysis record not found"}

    if analysis.status in ["paid", "processing", "completed"]:
        return {"success": True, "analysis_id": analysis_id, "status": analysis.status}

    price_in_cents = int(round(analysis.price * 100))
    currency = analysis.currency.lower()

    if not is_stripe_configured():
        # Mock payment success
        mock_pi = f"pi_mock_{analysis_id}"
        update_analysis_status(
            analysis_id=analysis_id,
            status="paid",
            stripe_payment_intent_id=mock_pi
        )
        return {"success": True, "analysis_id": analysis_id, "payment_intent_id": mock_pi}

    org = get_organization(org_id)
    if not org or not org.stripe_customer_id:
        return {"success": False, "error": "Organization has no configured Stripe payment method."}

    try:
        # Create off-session PaymentIntent
        intent_kwargs = {
            "amount": price_in_cents,
            "currency": currency,
            "customer": org.stripe_customer_id,
            "description": f"Code Analysis for Org {org.name} (Analysis ID: {analysis_id})",
            "metadata": {"org_id": org_id, "analysis_id": analysis_id},
            "off_session": True,
            "confirm": True
        }
        if org.stripe_default_payment_method_id:
            intent_kwargs["payment_method"] = org.stripe_default_payment_method_id

        intent = stripe.PaymentIntent.create(**intent_kwargs)

        if intent.status == "succeeded":
            event_id = f"pi_success_{intent.id}"
            if not is_event_processed(event_id):
                mark_event_processed(event_id, "payment_intent.succeeded")

            update_analysis_status(
                analysis_id=analysis_id,
                status="paid",
                stripe_payment_intent_id=intent.id
            )
            return {"success": True, "analysis_id": analysis_id, "payment_intent_id": intent.id}
        else:
            update_analysis_status(analysis_id=analysis_id, status="payment_failed")
            return {"success": False, "error": f"Payment failed with status: {intent.status}"}

    except stripe.error.CardError as e:
        update_analysis_status(analysis_id=analysis_id, status="payment_failed")
        return {"success": False, "error": f"Card Error: {e.user_message or str(e)}"}
    except Exception as e:
        update_analysis_status(analysis_id=analysis_id, status="payment_failed")
        return {"success": False, "error": str(e)}
