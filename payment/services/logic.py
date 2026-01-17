from decimal import Decimal
from django.utils import timezone

from payment.models import Payment
from payment.services.stripe_checkout import create_checkout_session


def calculate_payment_amount(appointment, payment_type):
    price = appointment.price
    if payment_type == Payment.Type.CONSULTATION:
        return price
    if payment_type == Payment.Type.CANCELLATION_FEE:
        time_diff = appointment.booked_at - timezone.now()
        if time_diff.total_seconds() < 86400:
            return price * Decimal("0.5")
        return Decimal("0.0")
    if payment_type == Payment.Type.NO_SHOW_FEE:
        return price * Decimal("1.2")
    return price


def process_appointment_payment(appointment, payment_type):
    amount = calculate_payment_amount(appointment, payment_type)
    if amount <= 0:
        return None
    # fmt: off
    session = create_checkout_session(
        amount_usd=amount,
        title=f"{payment_type} for Appointment {appointment.id}"
    )
    # fmt: on

    return Payment.objects.create(
        appointment=appointment,
        session_id=session.id,
        session_url=session.url,
        money_to_pay=amount,
        payment_type=payment_type,
        status="PENDING",
    )
