"""Stripe integration — create checkout sessions and fetch recent payments."""
import os
import stripe
from loguru import logger


def _init():
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


def create_checkout_link() -> str:
    """Create a Stripe Payment Link for the ebook and return the URL."""
    _init()
    price_id = os.getenv("STRIPE_PRICE_ID", "")
    if not stripe.api_key or not price_id:
        return ""
    try:
        link = stripe.PaymentLink.create(line_items=[{"price": price_id, "quantity": 1}])
        return link.url
    except stripe.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return ""


def get_recent_sales(limit: int = 20) -> list[dict]:
    """Return recent successful Stripe payment intents."""
    _init()
    if not stripe.api_key:
        return []
    try:
        intents = stripe.PaymentIntent.list(limit=limit)
        return [
            {
                "id":       pi.id,
                "amount":   pi.amount / 100,
                "currency": pi.currency.upper(),
                "status":   pi.status,
                "created":  pi.created,
            }
            for pi in intents.auto_paging_iter()
            if pi.status == "succeeded"
        ]
    except stripe.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return []
