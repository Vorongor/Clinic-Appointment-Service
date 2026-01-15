from celery import shared_task
from django.utils import timezone

from .telegram_helper import send_telegram_message
from appointment.models import Appointment


@shared_task
def notify_admin_task(message):
    send_telegram_message(message)


@shared_task
def check_no_shows_daily():
    no_show_appointments = Appointment.objects.filter(
        status=Appointment.Status.BOOKED,
        doctor_slot__end__lt=timezone.now(), # ForeignKey to model - DoctorSlot, field - end
    )

    if not no_show_appointments.exists():
        send_telegram_message("No missed appointments today!")
        return

    count = no_show_appointments.count()

    no_show_appointments.update(status=Appointment.Status.NO_SHOW)

    send_telegram_message(f"Daily update: {count} appointment(s) marked as NO_SHOW")
