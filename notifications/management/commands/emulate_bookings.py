from django.core.management.base import BaseCommand
from appointment.models import Appointment, DoctorSlot
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Makes fake appointments to trigger telegram notifications"

    def add_arguments(self, parser):
        parser.add_argument("total", type=int, help="How many appointments to create")

    def handle(self, *args, **kwargs):
        total = kwargs["total"]
        patient = User.objects.filter(is_staff=False).first()
        slots = DoctorSlot.objects.filter(appointment__isnull=True)[:total]

        if not slots.exists():
            self.stdout.write(self.style.ERROR("No free slots!"))
            return

        for slot in slots:
            # this triggers save() method in Appointment model and signals
            app = Appointment.objects.create(
                doctor_slot=slot,
                patient=patient,
                status="Booked"
            )
            self.stdout.write(f"Made an appointment #{app.id} to {slot.doctor}")
