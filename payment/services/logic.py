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
            stripe_session = stripe.checkout.Session.retrieve(
                payment.session_id)

            if getattr(stripe_session, "payment_status", None) == "paid":
                payment.status = Payment.Status.PAID
                payment.save(update_fields=["status"])
                return payment

            if (getattr(stripe_session, "status", None) == "open"
                    and stripe_session.url):
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


def calculate_payment_amount(appointment, payment_type, time_diff=None):
    user = appointment.patient

    price = appointment.price
    if user.has_penalty:
        logger.info(
            f"User has penalty for appointment {user.has_penalty} "
        )
        price += user.has_penalty

    if payment_type == Payment.Type.CONSULTATION:
        return price

    if payment_type == Payment.Type.CANCELLATION_FEE:
        if time_diff and time_diff < timedelta(hours=24):
            return price * Decimal("0.5")
        return Decimal("0.0")

    if payment_type == Payment.Type.NO_SHOW_FEE:
        return price * Decimal("1.2")

    return price


def _handle_consultation(appointment, amount):
    """Logic for creating a regular 100% payment."""
    return create_new_payment_or_update(
        appointment,
        amount,
        Payment.Type.CONSULTATION
    )


def _handle_cancellation(appointment, remaining_time):
    """Cancellation logic (100% or 50% refund/payment)."""
    existing_payment = appointment.payments.filter(
        status=Payment.Status.PAID).first()
    pending_payment = appointment.payments.filter(
        status=Payment.Status.PENDING).first()

    if remaining_time > timedelta(hours=24):
        if existing_payment:
            make_refund(
                existing_payment,
                percentage=100
            )
        if pending_payment:
            expire_stripe_session(pending_payment)
        payment_to_use = pending_payment or existing_payment
        return create_new_payment_or_update(
            payment_to_use.appointment,
            Decimal("0.0"),
            Payment.Type.CANCELLATION_FEE
        )

    else:
        amount = calculate_payment_amount(
            appointment,
            Payment.Type.CANCELLATION_FEE,
            remaining_time
        )
        if existing_payment:
            make_refund(existing_payment, percentage=50)
            return existing_payment
        return create_new_payment_or_update(
            appointment,
            amount,
            Payment.Type.CANCELLATION_FEE
        )


def _handle_no_show(appointment):
    """The logic of the penalty for non-appearance"""
    amount = calculate_payment_amount(appointment, Payment.Type.NO_SHOW_FEE)

    return create_new_payment_or_update(
        appointment,
        amount,
        Payment.Type.NO_SHOW_FEE
    )


def process_appointment_payment(appointment, payment_type):
    """Updated main helper."""
    remaining_time = appointment.booked_at - timezone.now()

    if payment_type == Payment.Type.CONSULTATION:
        amount = calculate_payment_amount(appointment, payment_type)
        return _handle_consultation(appointment, amount)

    if payment_type == Payment.Type.CANCELLATION_FEE:
        return _handle_cancellation(appointment, remaining_time)

    if payment_type == Payment.Type.NO_SHOW_FEE:
        return _handle_no_show(appointment)

    return None


def expire_stripe_session(payment):
    try:
        if payment.session_id:
            stripe.checkout.Session.expire(payment.session_id)
    except Exception as e:
        logger.warning(f"Could not expire session {payment.session_id}: {e}")


def make_refund(payment, percentage):
    """Stripe Refund."""

    if not payment.stripe_payment_intent_id:
        try:
            session = stripe.checkout.Session.retrieve(payment.session_id)
            if session.payment_intent:
                payment.stripe_payment_intent_id = session.payment_intent
                payment.save()
            else:
                logger.error(
                    f"Session {payment.session_id} has no "
                    "PaymentIntent yet (unpaid?)"
                )
                return False
        except Exception as e:
            logger.error(f"Failed to retrieve session from Stripe: {e}")
            return False

    try:
        refund_amount = (payment.money_to_pay
                         * (Decimal(percentage) / Decimal(100))
                         )
        logger.info(
            f"Refunding {percentage}%: {refund_amount} for payment {payment.id}")

        amount_to_refund = int(refund_amount) * 100

        if amount_to_refund <= 0:
            logger.warning(
                f"Refund amount for payment {payment.id} is 0. Skipping.")
            return False

        refund = stripe.Refund.create(
            payment_intent=payment.stripe_payment_intent_id,
            amount=amount_to_refund,
        )
        payment.money_to_pay = payment.money_to_pay - refund_amount
        payment.status = Payment.Status.REFUNDED if (percentage == 100) \
            else Payment.Status.PARTIALLY_REFUNDED
        payment.save()

        logger.info(
            f"Successfully refunded {percentage}% "
            f"({amount_to_refund / 100:.2f} USD) "
            f"for payment {payment.id}. Refund ID: {refund.id}")
        return True

    except stripe.error.StripeError as e:
        logger.error(f"Stripe Refund Error for payment {payment.id}: {str(e)}")
        return False


def create_new_payment_or_update(appointment, amount, payment_type):
    """Creates a Stripe session and a DB record."""
    existing = appointment.payments.first()

    new_session = create_checkout_session(
        amount_usd=amount,
        title=f"{payment_type} for Appointment {appointment.id}"
    )

    if existing:
        expire_stripe_session(existing)
        existing.money_to_pay = amount
        existing.payment_type = payment_type
        existing.session_id = new_session.id
        existing.session_url = new_session.url
        existing.save()
        return existing

    return Payment.objects.create(
        appointment=appointment,
        session_id=new_session.id,
        session_url=new_session.url,
        money_to_pay=amount,
        payment_type=payment_type,
        status=Payment.Status.PENDING,
    )
