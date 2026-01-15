from decimal import Decimal
from django.conf import settings
import stripe


def to_cents(amount: Decimal) -> int:
    amount = amount.quantize(Decimal("0.01"))
    return int(amount * 100)


def create_checkout_session(*, amount_usd: Decimal, title: str):
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not set")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": title},
                    "unit_amount": to_cents(amount_usd),
                },
                "quantity": 1,
            }
        ],
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
    )
    return session
