from django.contrib import admin

from .models import Doctor, DoctorSlot


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "price_per_visit")
    search_fields = ("first_name", "last_name")
    filter_horizontal = ("specializations",)


@admin.register(DoctorSlot)
class DoctorSlotAdmin(admin.ModelAdmin):
    list_display = ("doctor", "start", "end", "created_at")
    list_filter = ("doctor",)
    search_fields = ("doctor__first_name", "doctor__last_name")
