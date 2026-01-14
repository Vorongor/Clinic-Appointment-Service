from rest_framework import serializers

from appointment.models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = (
            "id",
            "doctor",
            "patient",
            "status",
            "booked_at",
            "completed_at",
            "price",
        )
        read_only_fields = (
            "id",
            "booked_at",
        )


class AppointmentDetailSerializer(serializers.ModelSerializer):
    pass


class AppointmentListSerializer(serializers.ModelSerializer):
    pass
