from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Patient


class UserSerializer(serializers.ModelSerializer):
    has_penalty = serializers.ReadOnlyField()

    class Meta:
        model = get_user_model()
        fields = (
            "id", "email", "password", "first_name",
            "last_name", "is_staff", "has_penalty"
        )
        read_only_fields = ("id", "is_staff", "has_penalty")
        extra_kwargs = {
            "password": {
                "write_only": True,
                "min_length": 5,
                "style": {"input_type": "password"},
                "label": _("Password"),
            }
        }


class PatientSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    total_unpaid_amount = serializers.ReadOnlyField()

    class Meta:
        model = Patient
        fields = (
            "id", "user", "email", "birth_date",
            "phone_number", "gender", "total_unpaid_amount"
        )
        read_only_fields = ("id", "user", "total_unpaid_amount")
