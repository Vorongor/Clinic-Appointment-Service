from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from appointment.filters import AppointmentFilter
from appointment.models import Appointment
from appointment.serializers import (
    AppointmentSerializer,
    AppointmentListSerializer,
    AppointmentDetailSerializer,
)


class AppointmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    action_serializers = {
        "retrieve": AppointmentDetailSerializer,
        "list": AppointmentListSerializer,
    }

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "doctor__first_name",
        "doctor__last_name",
    ]
    filterset_class = AppointmentFilter

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Appointment.objects.all()
        return Appointment.objects.filter(patient_id=user.id)

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)

    @action(
        methods=["POST"],
        detail=True,
        url_path="cancel",
        permission_classes=[IsAuthenticated],
    )
    def cancel_appointment(self, request, pk=None):
        pass

    @action(
        methods=["POST"],
        detail=True,
        url_path="completed",
        permission_classes=[IsAuthenticated],
    )
    def complete_appointment(self, request, pk=None):
        pass
