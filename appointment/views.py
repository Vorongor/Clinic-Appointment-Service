from django.db.models import Subquery, OuterRef

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)
from rest_framework import viewsets, filters, serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from appointment.filters import AppointmentFilter
from appointment.models import Appointment
from appointment.serializers import (
    AppointmentSerializer,
    AppointmentListSerializer,
    AppointmentDetailSerializer,
)
from appointment.actions import AppointmentActionsMixin
from payment.models import Payment


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "limit"
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response(
            {
                "links": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "results": data,
            }
        )


@extend_schema_view(
    list=extend_schema(
        summary="Filtering and searching",
        description="Searching by doctor last name, patient last name "
        "Filtering by date-from-to, exact date, patient id, doctor",
        parameters=[
            OpenApiParameter(
                # fmt: off
                name="search",
                description="Searching by doctor last name "
                            "or patient last name",
                required=False,
                type=str,
                # fmt: on
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                description="Filtering by status",
                enum=["BOOKED", "COMPLETED", "CANCELED", "NO_SHOW"],
            ),
            OpenApiParameter(
                name="doctor_id",
                type=OpenApiTypes.INT,
                description="For filtering by doctor id",
            ),
            OpenApiParameter(
                name="patient_id",
                type=OpenApiTypes.INT,
                description="Filtering by list of patients of exact patient",
            ),
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                description="Start date(YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                description="End date(YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="date_exact",
                type=OpenApiTypes.DATE,
                description="Exact date(YYYY-MM-DD)",
            ),
        ],
    ),
    create=extend_schema(
        summary="Booking appointment",
        description="Creating new appointment. Patient field "
        "substituted automatically, admin can book "
        "for anyone",
    ),
    retrieve=extend_schema(
        summary="Retrieving appointment",
        description="Retrieving appointment. Extended doctor, patient "
        "description. Additional payment information",
    ),
)
class AppointmentViewSet(AppointmentActionsMixin, viewsets.ModelViewSet):
    """
    Here we implemented: searching, filtering logic,
    getting query set due to permissions (admin, user),
    perform create patient.
    Custom actions: canceling , completing , no show with
    signal tracking (changing payment method)
    """

    permission_classes = [IsAuthenticated]
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    pagination_class = StandardResultsSetPagination
    action_serializers = {
        "retrieve": AppointmentDetailSerializer,
        "list": AppointmentListSerializer,
    }

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = [
        "patient__last_name",
        "doctor_slot__doctor__last_name",
    ]
    filterset_class = AppointmentFilter
    ordering = ["-booked_at"]

    def get_serializer_class(self):
        if self.action in [
            "cancel_appointment",
            "completed_appointment",
            "no_show_appointment",
        ]:
            return serializers.Serializer
        return self.action_serializers.get(self.action, self.serializer_class)

    def get_queryset(self):
        """
        User can only see own appointments.
        Staff can see all appointments.
        """
        last_payment_status = Payment.objects.filter(
            appointment=OuterRef("pk")
        ).order_by("-created_at").values("status")[:1]

        query = (
            Appointment.objects.all()
            .annotate(last_payment_status_annotated=Subquery(last_payment_status))
            .select_related("patient", "doctor_slot")
        )
        user = self.request.user
        if user.is_staff:
            return query
        return query.filter(patient_id=user.id)

    def perform_create(self, serializer):
        """
        Set user as patient, and set constant price
        """
        user = self.request.user
        patient = serializer.validated_data.get("patient", user)

        serializer.save(
            patient=patient,
        )
