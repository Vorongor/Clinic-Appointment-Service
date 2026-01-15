from django.contrib import admin

from payment.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "payment_type", "status", "appointment", "money_to_pay", "created_at")
    list_filter = ("status", "payment_type")
    search_fields = ("session_id",)
