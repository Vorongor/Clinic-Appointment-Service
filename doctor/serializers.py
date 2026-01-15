from rest_framework import serializers
from datetime import timedelta

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context.get("nested_create"):
            self.fields["doctor"].read_only = True

    def validate(self, data):
        start = data.get("start")
        end = data.get("end")
        if start and end and start >= end:
            raise serializers.ValidationError("start must be before end")
        return data


class DoctorSlotDetailSerializer(serializers.ModelSerializer):
    doctor = DoctorSerializer(read_only=True)

    class Meta:
        model = DoctorSlot
        fields = ["id", "doctor", "start", "end", "created_at"]
        read_only_fields = ["id", "doctor", "start", "end", "created_at"]


class DoctorSlotIntervalSerializer(serializers.Serializer):
    """
    Serializer for bulk creating slots from time intervals.
    """
    interval_start = serializers.DateTimeField(
        required=True,
        help_text="Start time of the interval"
    )
    interval_end = serializers.DateTimeField(
        required=True,
        help_text="End time of the interval"
    )
    duration = serializers.IntegerField(
        required=True,
        help_text="Slot duration in minutes"
    )

    def validate(self, data):
        interval_start = data.get("interval_start")
        interval_end = data.get("interval_end")
        duration = data.get("duration")
        
        if interval_start >= interval_end:
            raise serializers.ValidationError(
                "interval_start must be before interval_end"
            )
        
        if duration <= 0:
            raise serializers.ValidationError(
               "duration must be positive (in minutes)" 
            )

        return data

    def generate_slots(self):
        """Generate list of (start, end) tuples from interval."""
        data = self.validated_data
        interval_start = data["interval_start"]
        interval_end = data["interval_end"]
        duration_mins = data["duration"]
        duration = timedelta(minutes=duration_mins)

        slots = []
        current_start = interval_start
        while current_start + duration <= interval_end:
            current_end = current_start + duration
            slots.append((current_start, current_end))
            current_start = current_end

        return slots
