from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from appointment.models import Appointment
from doctor.models import DoctorSlot
from doctor.serializers import DoctorSlotDetailSerializer
from payment.serializers import PaymentSerializer
from user.serializers import UserSerializer


User = get_user_model()


class AppointmentSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )
    """
    Excluding all appointments in the past and with status booked,
    completed, no show to better user-friendly design
    """
    doctor_slot = serializers.PrimaryKeyRelatedField(
        queryset=DoctorSlot.objects.filter(
            start__gt=timezone.now(),
        ).exclude(appointment__status__in=["BOOKED", "COMPLETED", "NO_SHOW"]),
        label="Free slot",
    )

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
            "status",
            "booked_at",
            "completed_at",
            "price",
        )

    def __init__(self, *args, **kwargs):
        """
        User CAN'T book appointment for another user,
        this is available only for admins
        """
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user:
            if not request.user.is_staff:
                self.fields["patient"].read_only = True
                self.fields["patient"].queryset = None

    def validate(self, attrs):
        """
        Complex validation - debt, slot, time
        Users can book only for themselves
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

        if user.is_authenticated and user.has_penalty:
            raise serializers.ValidationError(
                {
                    "detail": "You cannot book a new appointment "
                    "until you pay pending invoices."
                }
            )

        return attrs


class AppointmentDetailSerializer(AppointmentSerializer):
    doctor_slot = DoctorSlotDetailSerializer(read_only=True)
    patient = UserSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True, source="payments", many=True)

    class Meta(AppointmentSerializer.Meta):
        fields = AppointmentSerializer.Meta.fields + ("payment",)


class AppointmentListSerializer(AppointmentSerializer):
    doctor_slot = serializers.StringRelatedField(read_only=True)
    patient = serializers.StringRelatedField(read_only=True)
    payment_status = serializers.SerializerMethodField()

    class Meta(AppointmentSerializer.Meta):
        fields = AppointmentSerializer.Meta.fields + ("payment_status",)

    def get_payment_status(self, appointment):
        last_payment = appointment.payments.order_by("-created_at").first()
        if last_payment:
            return last_payment.status
        return None


class CustomActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ("id", "doctor_slot", "patient", "status")
        read_only_fields = fields
