from datetime import timedelta

from django.utils import timezone

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from appointment.filters import AppointmentFilter
from appointment.models import Appointment
from appointment.serializers import (
    AppointmentSerializer,
    AppointmentListSerializer,
    AppointmentDetailSerializer,
)


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Here we implemented: searching, filtering logic,
    getting query set due to permissions (admin, user),
    perform create patient.
    Custom actions: canceling , completing , no show with transaction logic

    """

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

    def get_serializer_class(self):
        return self.action_serializers.get(self.action, self.serializer_class)

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
        appointment = self.get_object()

        if appointment.status != appointment.Status.BOOKED:
            return Response(
                {"error": f"You can't cancel appointment with this status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = appointment.Status.CANCELLED
        appointment.save()

        try:
            with transaction.atomic():
                time_until_appointment = appointment.booked_at - timezone.now()

                if time_until_appointment < timedelta(hours=24):
                    self._create_payment(appointment, payment_type="CANCELLATION_FEE")

            return Response({"status": "Appointment cancelled successfully"})

        except Exception as e:
            return Response(
                {"error": f"Transaction failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        methods=["POST"],
        detail=True,
        url_path="completed",
        permission_classes=[IsAdminUser],
    )
    def completed_appointment(self, request, pk=None):
        appointment = self.get_object()

        if appointment.status != appointment.Status.BOOKED:
            return Response(
                {
                    "error": f"Cannot complete appointment with status: {appointment.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                appointment.status = appointment.Status.COMPLETED
                appointment.completed_at = timezone.now()
                appointment.save()

                self._create_payment(appointment, payment_type="CONSULTATION")

            return Response({"status": "Appointment completed and payment created."})

        except Exception as e:
            return Response(
                {"error": f"Transaction failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        methods=["POST"],
        detail=True,
        url_path="no-show",
        permission_classes=[IsAdminUser],
    )
    def no_show_appointment(self, request, pk=None):
        appointment = self.get_object()

        if appointment.status != appointment.Status.BOOKED:
            return Response(
                {"error": f"You can't mark this appointment as 'No show'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if appointment.booked_at > timezone.now():
            return Response(
                {
                    "error": "You cannot mark as 'No Show' before the appointment time starts."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = appointment.Status.NO_SHOW
        appointment.save()

        try:
            with transaction.atomic():
                self._create_payment(appointment, payment_type="NO_SHOW_FEE")

            return Response(
                {
                    "status": "Success",
                    "message": "Appointment marked as 'No Show'. 120% penalty fee applied.",
                }
            )

        except Exception as e:
            return Response(
                {"error": f"Transaction failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _create_payment(self, appointment, payment_type):
        pass
