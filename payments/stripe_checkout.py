"""
Stripe payment integration — sell the Best Brand Co. app from bestbrand.ca.

Flow:
  1. Visitor clicks Buy on bestbrand.ca → POST /payments/create-checkout
  2. Server creates Stripe Checkout Session → returns URL
  3. Visitor pays on Stripe-hosted page
  4. Stripe redirects to /payments/success?session_id=xxx
  5. Server verifies payment → shows download links
  6. Stripe also fires a webhook → /payments/webhook (server-side confirmation)
"""
from __future__ import annotations
import hashlib
import hmac
import time
import secrets
from loguru import logger

# Download tokens valid for 24 hours (stored in memory — restart clears them)
_valid_tokens: dict[str, float] = {}   # token → expiry timestamp
TOKEN_TTL = 86_400                      # 24 hours

DOWNLOAD_LINKS = {
    "windows": "https://github.com/fmproductline-wq/bbc/releases/latest/download/BestBrand-Windows.zip",
    "mac":     "https://github.com/fmproductline-wq/bbc/releases/latest/download/BestBrand-Mac.dmg",
    "linux":   "https://github.com/fmproductline-wq/bbc/releases/latest/download/BestBrand-Linux.tar.gz",
}


def _stripe():
    """Lazy-import stripe so the app starts without it if key not set."""
    import stripe as _s
    from config import cfg
    _s.api_key = cfg.STRIPE_SECRET_KEY
    return _s


def create_checkout_session(success_url: str, cancel_url: str) -> str:
    """
    Create a Stripe Checkout Session and return the hosted checkout URL.
    Raises if Stripe is not configured.
    """
    from config import cfg
    if not cfg.STRIPE_SECRET_KEY or not cfg.STRIPE_PRICE_ID:
        raise RuntimeError("STRIPE_SECRET_KEY and STRIPE_PRICE_ID must be set in .env")

    stripe = _stripe()
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": cfg.STRIPE_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"product": "bestbrand_app_v2"},
    )
    logger.info(f"Stripe checkout created: {session.id}")
    return session.url


def verify_session(session_id: str) -> bool:
    """Return True if the Stripe session was paid."""
    stripe = _stripe()
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == "paid"
    except Exception as e:
        logger.error(f"Stripe session verify error: {e}")
        return False


def issue_download_token() -> str:
    """Generate a one-time download token valid for 24 hours."""
    token = secrets.token_urlsafe(32)
    _valid_tokens[token] = time.time() + TOKEN_TTL
    return token


def consume_token(token: str) -> bool:
    """
    Validate a download token. Keeps it valid for the full 24h window
    (lets the user download multiple platforms with one purchase).
    """
    expiry = _valid_tokens.get(token)
    if not expiry:
        return False
    if time.time() > expiry:
        del _valid_tokens[token]
        return False
    return True


def verify_stripe_webhook(payload: bytes, sig_header: str, webhook_secret: str) -> dict | None:
    """Verify Stripe webhook signature and return the event dict, or None on failure."""
    stripe = _stripe()
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        return event
    except Exception as e:
        logger.error(f"Stripe webhook verify failed: {e}")
        return None
