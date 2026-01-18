from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from appointment.models import Appointment, DoctorSlot
from django.contrib.auth import get_user_model
from notifications.tasks import check_no_shows_daily

User = get_user_model()


class Command(BaseCommand):
    """Emulate expired records and run the check_no_shows_daily task"""

    def handle(self, *args, **kwargs):
        self.stdout.write("Prepare data for No-Show test...")

        user = User.objects.filter(is_staff=False).first()
        doctor_slot = DoctorSlot.objects.first()

        if not doctor_slot:
            self.stdout.write(self.style.ERROR(
                "Make at least one slot for creation!"
            ))
            return

        past_start = timezone.now() - timedelta(hours=2)
        past_end = timezone.now() - timedelta(hours=1)

        test_slot = DoctorSlot.objects.create(
            doctor=doctor_slot.doctor,
            start=past_start,
            end=past_end
        )

        appt = Appointment.objects.create(
            doctor_slot=test_slot,
            patient=user,
            status=Appointment.Status.BOOKED
        )

        self.stdout.write(self.style.SUCCESS(
            f"An expired entry has been created #{appt.id} "
            f"(Ended in {past_end})"
        ))

        self.stdout.write("Running a task check_no_shows_daily...")
        check_no_shows_daily()

        self.stdout.write(self.style.SUCCESS("Test completed. Check Telegram"))
