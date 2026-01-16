from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from django.db.models import Exists, OuterRef
from django_filters.rest_framework import DjangoFilterBackend
from user.permissions import IsAdminOrReadOnly

from .models import Doctor, DoctorSlot
from .serializers import (
    DoctorSerializer,
    DoctorSlotSerializer,
    DoctorSlotDetailSerializer,
    DoctorSlotIntervalSerializer
)
from appointment.models import Appointment


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["specializations"]
    permission_classes = [IsAdminOrReadOnly]


class DoctorSlotNestedViewSet(viewsets.GenericViewSet):
    """
    Nested viewset for /doctors/<doctor_id>/slots/
    Supports GET list (with filters) and POST bulk-create via intervals.
    """
    serializer_class = DoctorSlotIntervalSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        doctor_id = self.kwargs["doctor_pk"]
        qs = DoctorSlot.objects.filter(doctor_id=doctor_id)

        from_param = self.request.query_params.get("from")
        to_param = self.request.query_params.get("to")
        if from_param:
            qs = qs.filter(start__gte=from_param)
        if to_param:
            qs = qs.filter(end__lte=to_param)

        available_only = self.request.query_params.get("available_only")
        if available_only in ["true", "True", "1"]:
            qs = qs.filter(
                ~Exists(
                    Appointment.objects.filter(
                        doctor_slot=OuterRef('pk'),
                        status=Appointment.Status.BOOKED
                    )
                )
            )

        return qs

    def list(self, request, doctor_pk=None):
        qs = self.get_queryset()
        serializer = DoctorSlotSerializer(qs, many=True)
        return Response(serializer.data)

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

            serializer = DoctorSlotSerializer(data=normalized, many=True, context={"nested_create": True})
            serializer.is_valid(raise_exception=True)
            slots = [(d["start"], d["end"]) for d in serializer.validated_data]

        elif isinstance(data, dict):
            interval_ser = DoctorSlotIntervalSerializer(data=data)
            interval_ser.is_valid(raise_exception=True)
            slots = interval_ser.generate_slots()

        else:
            return Response(
                {"detail": "Expected a list of slots or an interval object"},
                status=status.HTTP_400_BAD_REQUEST
            )

        created = []
        for start, end in slots:
            slot = DoctorSlot.objects.create(
                doctor_id=doctor_pk,
                start=start,
                end=end
            )
            created.append(slot)

        out_serializer = DoctorSlotSerializer(created, many=True)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class DoctorSlotViewSet(
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

    def destroy(self, request, pk=None):
        slot = self.get_object()
        if slot.appointments.exists():
            return Response(
                {"detail": "Cannot delete slot with existing appointments"},
                status=status.HTTP_400_BAD_REQUEST
            )
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
