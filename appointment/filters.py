from random import choices

from django_filters import rest_framework as filters

from appointment.models import Appointment


class AppointmentFilter(filters.FilterSet):
    booked_from = filters.DateFilter(
        field_name="booked_from",
        lookup_expr="gte",
        label="Booked from (date)",
        input_formats=["%Y-%m-%d"],
    )
    booked_to = filters.DateFilter(
        field_name="booked_to",
        lookup_expr="lte",
        label="Booked to (date)",
        input_formats=["%Y-%m-%d"],
    )
    booked_exact = filters.DateFilter(
        field_name="booked_exact",
        lookup_expr="date",
        label="Exact booking date",
    )
    patient_id = filters.NumberFilter(
        field_name="patient_id",
        label="Patient ID",
    )
    doctor_id = filters.NumberFilter(
        field_name="doctor_slot__doctor_id",
        label="Doctor ID",
    )
    status = filters.ChoiceFilter(
        choices=Appointment.Status.choices,
        label="Appointment status",
    )

    class Meta:
        model = Appointment
        fields = [
            "booked_from",
            "booked_to",
            "booked_exact",
            "patient_id",
            "doctor_id",
            "status",
        ]
