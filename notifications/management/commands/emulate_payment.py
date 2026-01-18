from django.core.management.base import BaseCommand
from payment.models import Payment
from appointment.models import Appointment


class Command(BaseCommand):
    """Emulates a successful payment of the last created payment"""

    def handle(self, *args, **kwargs):
        payment = Payment.objects.filter(status=Payment.Status.PENDING).first()

        if not payment:
            self.stdout.write(self.style.ERROR("There are no payments "
                                               "with the status PENDING"))
            return

        self.stdout.write(f"We pay the payment #{payment.id} "
                          f"for recording #{payment.appointment.id}...")

        payment.status = Payment.Status.PAID
        payment.save()  # This triggers payment_notification_signal

        appointment = payment.appointment
        appointment.status = Appointment.Status.BOOKED
        appointment.save()  # This triggers appointment_notification_signal

        self.stdout.write(self.style.SUCCESS("Success! Check Telegram"))
