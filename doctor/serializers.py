from rest_framework import serializers

from .models import Doctor, DoctorSlot
from specializations.models import Specialization


class DoctorSerializer(serializers.ModelSerializer):
    specializations = serializers.PrimaryKeyRelatedField(
        queryset=Specialization.objects.all(),
        many=True
    )

    class Meta:
        model = Doctor
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "specializations",
            "price_per_visit",
        ]


class DoctorSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSlot
        fields = ["id", "doctor", "start", "end", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        start = data.get("start")
        end = data.get("end")
        if start and end and start >= end:
            raise serializers.ValidationError("start must be before end")
        return data
