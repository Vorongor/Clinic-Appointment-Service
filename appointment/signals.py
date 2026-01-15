import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from appointment.models import Appointment
from payment.tasks import create_stripe_payment_task

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Appointment)
def create_payment_signal_handler(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(
            lambda: create_stripe_payment_task.delay(instance.id)
        )