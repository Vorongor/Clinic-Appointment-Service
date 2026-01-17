import django_filters
from django.db.models import Exists, OuterRef
from .models import Doctor, DoctorSlot
from appointment.models import Appointment


class DoctorFilter(django_filters.FilterSet):
    specializations = django_filters.CharFilter(
        field_name="specializations__name", lookup_expr="icontains"
    )

    class Meta:
        model = Doctor
        fields = ["specializations"]


class DoctorSlotFilter(django_filters.FilterSet):
    from_date = django_filters.DateTimeFilter(
        field_name="start", lookup_expr="gte", label="From Date"
    )
    to_date = django_filters.DateTimeFilter(
        field_name="end", lookup_expr="lte", label="To Date"
    )
    available_only = django_filters.BooleanFilter(
        method="filter_available_only", label="Available Only"
    )

    def filter_available_only(self, queryset, name, value):
        if value:
            return queryset.filter(
                ~Exists(
                    Appointment.objects.filter(
                        doctor_slot=OuterRef("pk"),
                        status=Appointment.Status.BOOKED
                    )
                )
            )
        return queryset

    class Meta:
        model = DoctorSlot
        fields = ["from_date", "to_date", "available_only"]
