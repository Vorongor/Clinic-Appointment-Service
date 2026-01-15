from django.utils import timezone
from rest_framework import serializers

from appointment.models import Appointment
from doctor.serializers import DoctorSlotSerializer
from user.serializers import UserSerializer


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = (
            "id",
            "doctor_slot",
            "patient",
            "status",
            "booked_at",
            "completed_at",
            "price",
        )
        read_only_fields = (
            "id",
            "patient",
            "status",
            "booked_at",
            "completed_at",
            "price",
        )

    def validate(self, attrs):
        """
        Complex validation - debt, slot, time
        """
        slot = attrs.get("doctor_slot")
        user = self.context["request"].user

        if slot.start < timezone.now():
            raise serializers.ValidationError(
                {"doctor_slot": "You cannot book a slot in the past."}
            )

        is_taken = (
            Appointment.objects.filter(doctor_slot=slot)
            .exclude(status=Appointment.Status.CANCELLED)
            .exists()
        )

        if is_taken:
            raise serializers.ValidationError(
                {"doctor_slot": "This slot is already booked by another patient."}
            )

        # has_debt = Payment.objects.filter(
        #     appointment__patient=user,
        #     status="FAILED",
        # ).exists()
        #
        # if has_debt:
        #     raise serializers.ValidationError(
        #         "You have unpaid penalties. Booking is blocked until payment."
        #     )
        #
        # return attrs


class AppointmentDetailSerializer(AppointmentSerializer):
    doctor_slot = DoctorSlotSerializer(read_only=True)
    patient = UserSerializer(read_only=True)


class AppointmentListSerializer(AppointmentSerializer):
    doctor = serializers.StringRelatedField(read_only=True)
    patient = serializers.StringRelatedField(read_only=True)
