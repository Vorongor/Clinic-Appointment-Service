import stripe
from celery import shared_task
from celery.utils.time import timezone

from appointment.models import Appointment
from payment.models import Payment
from payment.services.logic import process_appointment_payment
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def create_stripe_payment_task(self, appointment_id, payment_type_value):
    try:
        instance = Appointment.objects.get(id=appointment_id)
        process_appointment_payment(
            appointment=instance, payment_type=payment_type_value
        )
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
    except Exception as exc:
        logger.error(f"Error creating payment for {appointment_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def sync_pending_payments():
    pending_payments = Payment.objects.filter(
        status="PENDING",
        created_at__lt=timezone.now() - timezone.timedelta(minutes=15)
    )

    for payment in pending_payments:
        stripe_session = stripe.checkout.Session.retrieve(payment.session_id)

        if stripe_session.payment_status == "paid":
            payment.status = "PAID"
            payment.save()
        elif stripe_session.status == "expired":
            payment.status = "EXPIRED"
            payment.save()
