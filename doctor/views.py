from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from user.permissions import IsAdminOrReadOnly
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import Doctor, DoctorSlot
from .serializers import (
    DoctorSerializer,
    DoctorSlotSerializer,
    DoctorSlotDetailSerializer,
    DoctorSlotIntervalSerializer,
)
from .filters import DoctorFilter, DoctorSlotFilter


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DoctorFilter
    permission_classes = [IsAdminOrReadOnly]

    @extend_schema(
        summary="List doctors",
        description="Retrieve a list of doctors. "
                    "Filter by specialization code or id using the "
                    "'specialization' query parameter.",
        parameters=[
            OpenApiParameter(
                name="specialization",
                type=OpenApiTypes.STR,
                description="Filter doctors by specialization code or id",
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(
            self.get_queryset().prefetch_related("specializations")
        )
        queryset = queryset.distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DoctorSlotNestedViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    """
    Nested viewset for /doctors/<doctor_id>/slots/
    Supports GET list (with filters), POST bulk-create via intervals, and DELETE.
    """

    serializer_class = DoctorSlotIntervalSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DoctorSlotFilter
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        doctor_id = self.kwargs["doctor_pk"]
        return DoctorSlot.objects.filter(doctor_id=doctor_id)

    @extend_schema(
        summary="List doctor slots",
        description="Retrieve slots for a specific doctor, with "
                    "optional filters for date range and availability.",
        parameters=[
            OpenApiParameter(
                name="from_date",
                type=OpenApiTypes.DATETIME,
                description="Filter slots starting on or after this date",
            ),
            OpenApiParameter(
                name="to_date",
                type=OpenApiTypes.DATETIME,
                description="Filter slots ending on or before this date",
            ),
            OpenApiParameter(
                name="available_only",
                type=OpenApiTypes.STR,
                enum=["True", "False"],
                description="If True, show only slots "
                            "without booked appointment",
            ),
        ],
    )
    def list(self, request, doctor_pk=None):
        qs = self.get_queryset()
        filterset = self.filterset_class(request.GET, queryset=qs)
        qs = filterset.qs
        serializer = DoctorSlotSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create doctor slots",
        description="Create multiple slots for a doctor. "
                    "Accepts either a list of slot objects "
                    "or an interval object to generate slots.",
        request={
            "application/json": {
                "oneOf": [
                    {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "start": {"type": "string",
                                          "format": "date-time"},
                                "end": {"type": "string",
                                        "format": "date-time"},
                            },
                        },
                    },
                    {
                        "type": "object",
                        "properties": {
                            "interval_start": {"type": "string",
                                               "format": "date-time"},
                            "interval_end": {"type": "string",
                                             "format": "date-time"},
                            "duration": {"type": "integer"},
                        },
                    },
                ],
            },
        },
        responses={
            201: DoctorSlotSerializer(many=True),
        },
    )
    def create(self, request, doctor_pk=None):
        """
        POST /doctors/<id>/slots/

        Accepts list of explicit slots or
        interval-based generation
        """
        data = request.data
        slots = []

        if isinstance(data, list):
            normalized = []
            for slot_data in data:
                slot_copy = dict(slot_data)
                if "start_time" in slot_copy:
                    slot_copy["start"] = slot_copy.pop("start_time")
                if "end_time" in slot_copy:
                    slot_copy["end"] = slot_copy.pop("end_time")
                normalized.append(slot_copy)

            serializer = DoctorSlotSerializer(
                data=normalized, many=True, context={"nested_create": True}
            )
            serializer.is_valid(raise_exception=True)
            slots = [(d["start"], d["end"]) for d in serializer.validated_data]

        elif isinstance(data, dict):
            interval_ser = DoctorSlotIntervalSerializer(data=data)
            interval_ser.is_valid(raise_exception=True)
            slots = interval_ser.generate_slots()

        else:
            return Response(
                {"detail": "Expected list of slots or interval object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        for start, end in slots:
            slot = DoctorSlot.objects.create(doctor_id=doctor_pk, start=start,
                                             end=end)
            created.append(slot)

        out_serializer = DoctorSlotSerializer(created, many=True)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Delete a doctor slot",
        description="Delete a slot if it has no associated appointment.",
        responses={
            204: None,
            400: {
                "description": "Cannot delete slot "
                               "with existing appointment"},
        },
    )
    def destroy(self, request, doctor_pk=None, pk=None):
        slot = self.get_object()
        if slot.appointment.exists():
            return Response(
                {"detail": "Cannot delete slot with existing "
                           "appointment"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DoctorSlotViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    Flat viewset for /slots/<id>/
    Supports GET detail and DELETE (only if no appointment exists).
    """

    queryset = DoctorSlot.objects.all()
    serializer_class = DoctorSlotSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        """Use detail serializer for retrieve action."""
        if self.action == "retrieve":
            return DoctorSlotDetailSerializer
        return DoctorSlotSerializer

    @extend_schema(
        summary="Delete a doctor slot",
        description="Delete a slot if it has no associated appointment.",
        responses={
            204: None,
            400: {
                "description": "Cannot delete slot "
                               "with existing appointments"},
        },
    )
    def destroy(self, request, pk=None):
        slot = self.get_object()
        if slot.appointment.exists():
            return Response(
                {"detail": "Cannot delete slot with existing "
                           "appointment"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
