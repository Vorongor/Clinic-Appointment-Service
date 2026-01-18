from django.contrib import admin

from appointment.models import Appointment


@admin.register(Appointment)
class OrderAdmin(admin.ModelAdmin):
    """
    Operating appointments via django-admin
    """

    list_display = (
        "id",
        "doctor_slot",
        "patient",
        "status",
        "booked_at",
        "completed_at",
        "price",
    )
    list_filter = ("status", "patient", "doctor_slot__doctor__specializations")
    search_fields = (
        "patient__last_name",
        "patient__email",
        "patient__patient_profile__phone_number",
    )
    ordering = ("-booked_at", "status", "completed_at")
