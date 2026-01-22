from django.db import models

from appointment.models import Appointment


class Payment(models.Model):
    class Status(models.TextChoices):
        PARTIALLY_REFUNDED = ("PARTIALLY_REFUNDED", "Refunded 50% of price")
        REFUNDED = ("REFUNDED", "Refunded 100% of price")
        PENDING = ("PENDING", "Pending")
        PAID = ("PAID", "Paid")
        EXPIRED = ("EXPIRED", "Expired")

    class Type(models.TextChoices):
        CONSULTATION = ("CONSULTATION", "Consultation")
        CANCELLATION_FEE = ("CANCELLATION_FEE", "Cancellation fee")
        NO_SHOW_FEE = ("NO_SHOW_FEE", "No-show fee")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payment_type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.CONSULTATION
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    session_url = models.URLField(max_length=2048, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)

    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["appointment", "payment_type"],
                name="unique_appointment",
            )
        ]

    def __str__(self) -> str:
        return (f"Payment #{self.id} | {self.payment_type} | {self.status} "
                f"| appt #{self.appointment_id}")
