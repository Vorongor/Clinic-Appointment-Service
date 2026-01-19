from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Patient


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_staff")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone_number",
        "birth_date",
        "total_unpaid_amount_display",
        "penalty_status",
    )
    list_filter = ("gender",)
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "phone_number",
    )

    @admin.display(description="Total Debt")
    def total_unpaid_amount_display(self, obj):
        return f"{obj.total_unpaid_amount} USD"

    @admin.display(description="Penalty Status")
    def penalty_status(self, obj):
        penalty = obj.user.has_penalty
        if penalty:
            return f"Debt: {penalty} USD"
        return "No Penalty"
