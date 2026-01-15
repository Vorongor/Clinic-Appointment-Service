from celery import shared_task
from appointment.models import Appointment
from payment.models import Payment
from payment.services.stripe_checkout import create_checkout_session
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5)
def create_stripe_payment_task(self, appointment_id):
    try:
        instance = Appointment.objects.get(id=appointment_id)
        money_to_pay = instance.price
        payment_title = f"Payment for consultation appointment №{instance.id}"

        pay_session = create_checkout_session(
            amount_usd=money_to_pay,
            title=payment_title,
        )

        Payment.objects.create(
            appointment=instance,
            session_id=pay_session.id,
            session_url=pay_session.url,
            money_to_pay=money_to_pay,
        )
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
    except Exception as exc:
        # Якщо Stripe впав, Celery спробує ще раз через 60 секунд
        logger.error(f"Error creating payment for {appointment_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)