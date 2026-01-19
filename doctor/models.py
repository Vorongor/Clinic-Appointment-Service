from django.db import models
from django.conf import settings
from specializations.models import Specialization


class Doctor(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specializations = models.ManyToManyField(
        Specialization,
        related_name="doctors"
    )
    price_per_visit = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class DoctorSlot(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="slots"
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start"]
        unique_together = ("doctor", "start", "end")

    def __str__(self):
        return (
            f"Slot #{self.id} " f"| "
            f"Doctor - {self.doctor} | {self.start} - {self.end}"
        )

    @property
    def is_booked(self):
        return appointment.exists()