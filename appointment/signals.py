import logging
from datetime import timedelta

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from appointment.models import Appointment
from payment.models import Payment
from payment.tasks import create_stripe_payment_task

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Appointment)
def create_payment_signal_handler(sender, instance, created, **kwargs):
    """
    If we created appointment we call create_stripe_payment_task
    ----------------------------------------------------------------
    block else:
    If we patched appointment to status=COMPLETED and payment "CONSULTATION" exists - we do nothing,
    if payment doesn't exist - we will call create_stripe_payment_task with CONSULTATION
    ----------------------------------------------------------------
    If we patched appointment to status=NO_SHOW and payment with NO_SHOW_FEE exists - we do nothing,
    if payment doesn't exist - we will call create_stripe_payment_task with NO_SHOW_FEE
    ----------------------------------------------------------------
    If we patched appointment to status=CANCELLED and payment with CANCELLATION_FEE exists - we do nothing,
    if payment doesn't exist AND there is less than 24 hours left until the doctor's appointment
    we will call create_stripe_payment_task with CANCELLATION_FEE
    """
    if created and instance.status == "BOOKED":
        transaction.on_commit(
            lambda: create_stripe_payment_task.delay(
                instance.id, Payment.Type.CONSULTATION
            )
        )
    else:
        if instance.status == Appointment.Status.COMPLETED:
            has_payment = instance.payments.filter(
                payment_type=Payment.Type.CONSULTATION
            ).exists()

            if not has_payment:
                transaction.on_commit(
                    lambda: create_stripe_payment_task.delay(
                        instance.id, Payment.Type.CONSULTATION
                    )
                )
        elif instance.status == Appointment.Status.NO_SHOW:
            has_penalty = instance.payments.filter(
                payment_type=Payment.Type.NO_SHOW_FEE
            ).exists()

            if not has_penalty:
                transaction.on_commit(
                    lambda: create_stripe_payment_task.delay(
                        instance.id, Payment.Type.NO_SHOW_FEE
                    )
                )
        elif instance.status == Appointment.Status.CANCELLED:
            has_penalty = instance.payments.filter(
                payment_type=Payment.Type.CANCELLATION_FEE
            ).exists()
            if not has_penalty:
                transaction.on_commit(
                    lambda: create_stripe_payment_task.delay(
                        instance.id, Payment.Type.CANCELLATION_FEE
                    )
                )
