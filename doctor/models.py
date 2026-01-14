from django.db import models
from django.conf import settings
from specializations.models import Specialization


class Doctor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specializations = models.ManyToManyField(
        Specialization,
        related_name="doctors"
    )
    price_per_visit = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
