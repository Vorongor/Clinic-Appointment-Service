from decimal import Decimal
from django.utils import timezone

from payment.models import Payment
from payment.services.stripe_checkout import create_checkout_session


def calculate_payment_amount(appointment, payment_type):
    price = appointment.price
    if payment_type == "CONSULTATION":
        return price
    if payment_type == "CANCELLATION":
        time_diff = appointment.start_time - timezone.now()
        if time_diff.total_seconds() < 86400:
            return price * Decimal("0.5")
        return Decimal("0.0")
    if payment_type == "NO_SHOW":
        return price * Decimal("1.2")
    return price


def process_appointment_payment(appointment, payment_type):
    amount = calculate_payment_amount(appointment, payment_type)
    if amount <= 0:
        return None

    session = create_checkout_session(
        amount_usd=amount,
        title=f"{payment_type} for Appointment {appointment.id}"
    )

    return Payment.objects.create(
        appointment=appointment,
        session_id=session.id,
        session_url=session.url,
        money_to_pay=amount,
        payment_type=payment_type,
        status="PENDING"
    )
