import stripe
from celery import shared_task
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

from appointment.models import Appointment
from payment.models import Payment
from payment.services.logic import process_appointment_payment
import logging


logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


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
        status=Payment.Status.PENDING,
        created_at__lt=timezone.now() - timedelta(minutes=15)
    )

    for payment in pending_payments:
        try:
            if not payment.session_id:
                logger.warning(
                    f"Payment {payment.id} has no session_id. Skipping.")
                continue

            stripe_session = stripe.checkout.Session.retrieve(
                payment.session_id
            )

            if stripe_session.payment_status == "paid":
                payment.status = Payment.Status.PAID
                payment.save()
            elif stripe_session.status == "expired":
                payment.status = Payment.Status.EXPIRED
                payment.save()
            else:
                logger.info(
                    f"Payment {payment.id} still pending in "
                    f"Stripe (open/no_payment_required)")

        except Exception as e:
            logger.error(f"Error processing payment {payment.id}: {str(e)}")
