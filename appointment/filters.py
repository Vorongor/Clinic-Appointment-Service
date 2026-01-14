from django_filters import rest_framework as filters

from appointment.models import Appointment


class AppointmentFilter(filters.FilterSet):
    booked_at = filters.DateFromToRangeFilter(field_name="booked_at")
    patient_id = filters.NumberFilter(field_name="patient_id")
    doctor_id = filters.NumberFilter(field_name="doctor_id")
    status = filters.CharFilter(field_name="status")

    class Meta:
        model = Appointment
        fields = ["booked_at", "patient_id", "doctor_id", "status"]
