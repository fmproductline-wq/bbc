"""
Stripe integration — create checkout sessions and fetch recent payments.
"""
import stripe
from loguru import logger
from ..config import STRIPE_SECRET_KEY, STRIPE_PRICE_ID, STRIPE_SUCCESS_URL

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_link() -> str:
    """Create a Stripe Payment Link for the ebook and return the URL."""
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        return ""
    try:
        link = stripe.PaymentLink.create(
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        )
        return link.url
    except stripe.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return ""


def get_recent_sales(limit: int = 20) -> list[dict]:
    """Return recent successful Stripe payment intents."""
    if not STRIPE_SECRET_KEY:
        return []
    try:
        intents = stripe.PaymentIntent.list(limit=limit)
        return [
            {
                "id": pi.id,
                "amount": pi.amount / 100,
                "currency": pi.currency.upper(),
                "status": pi.status,
                "created": pi.created,
            }
            for pi in intents.auto_paging_iter()
            if pi.status == "succeeded"
        ]
    except stripe.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return []
