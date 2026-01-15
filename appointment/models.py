from django.conf import settings
from django.db import models

from doctor.models import DoctorSlot


class Appointment(models.Model):
    """
    Appointment model - core of the project,
    here described how booking should work
    """

    class Status(models.TextChoices):
        BOOKED = ("BOOKED", "Booked")
        COMPLETED = ("COMPLETED", "Completed")
        CANCELLED = ("CANCELLED", "Cancelled")
        NO_SHOW = ("NO_SHOW", "No Show")

    doctor_slot = models.ForeignKey(
        DoctorSlot, on_delete=models.CASCADE, related_name="appointment"
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments"
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.BOOKED
    )
    booked_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, editable=False)

    def __str__(self):
        return (
            f"Appointment #{self.id} | Doctor - {self.doctor} | "
            f"Patient - {self.patient.last_name} | {self.status}"
        )

    class Meta:
        """
        Ordered by last bookings
        """

        verbose_name = "appointment"
        verbose_name_plural = "appointments"
        ordering = [
            "-booked_at",
        ]
