import logging
from datetime import timedelta
from decimal import Decimal

import stripe
from django.utils import timezone

from payment.models import Payment
from payment.services.stripe_checkout import create_checkout_session

logger = logging.getLogger(__name__)


def renew_payment_session(payment: Payment) -> Payment:
    if payment.status == Payment.Status.PAID:
        raise ValueError("Paid payments can't be renewed")

    if payment.money_to_pay <= 0:
        raise ValueError("Nothing to pay for this payment")

    if payment.session_id:
        try:
            stripe_session = stripe.checkout.Session.retrieve(payment.session_id)

            if getattr(stripe_session, "payment_status", None) == "paid":
                payment.status = Payment.Status.PAID
                payment.save(update_fields=["status"])
                return payment

            if getattr(stripe_session, "status", None) == "open" and stripe_session.url:
                if payment.session_url != stripe_session.url:
                    payment.session_url = stripe_session.url
                    payment.save(update_fields=["session_url"])
                return payment

        except Exception:
            pass

    new_session = create_checkout_session(
        amount_usd=payment.money_to_pay,
        title=f"{payment.payment_type} for Appointment {payment.appointment_id}",
    )

    if payment.session_id and payment.session_id != new_session.id:
        try:
            stripe.checkout.Session.expire(payment.session_id)
        except Exception:
            pass

    payment.session_id = new_session.id
    payment.session_url = new_session.url
    payment.status = Payment.Status.PENDING
    payment.save(update_fields=["session_id", "session_url", "status"])
    return payment


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

    existing_payment = appointment.payments.filter(
        status=Payment.Status.PENDING
    ).first()

    if existing_payment:
        try:
            stripe.checkout.Session.expire(existing_payment.session_id)
        except Exception:
            logger.info(
                f"Free cancellation for appointment {appointment.id}. "
                f"No new session created.")
        remaining_time = appointment.booked_at - timezone.now()
        if (existing_payment.payment_type == Payment.Type.CANCELLATION_FEE
                and remaining_time > timedelta(hours=24)):
            try:
                stripe.checkout.Session.expire(existing_payment.session_id)
            except Exception as err:
                logger.warning(
                    f"Could not expire session for free cancellation: {err}")

            existing_payment.status = Payment.Status.EXPIRED
            existing_payment.payment_type = payment_type
            existing_payment.money_to_pay = Decimal("0.0")
            existing_payment.save()

            logger.info(
                f"Free cancellation for appointment {appointment.id}. "
                f"No new session created.")
            return existing_payment

    new_stripe_session = create_checkout_session(
        amount_usd=amount,
        title=f"{payment_type} for Appointment {appointment.id}"
    )

    if existing_payment:
        existing_payment.money_to_pay = amount
        existing_payment.payment_type = payment_type
        existing_payment.session_id = new_stripe_session.id
        existing_payment.session_url = new_stripe_session.url
        existing_payment.save()
        return existing_payment
    else:
        return Payment.objects.create(
            appointment=appointment,
            session_id=new_stripe_session.id,
            session_url=new_stripe_session.url,
            money_to_pay=amount,
            payment_type=payment_type,
            status=Payment.Status.PENDING,
        )
