from datetime import timedelta

from django.utils import timezone

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
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
from payment.models import Payment


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
        "doctor_slot__doctor__first_name",
        "doctor_slot__doctor__last_name",
    ]
    filterset_class = AppointmentFilter

    def get_serializer_class(self):
        return self.action_serializers.get(self.action, self.serializer_class)

    def get_queryset(self):
        """
        User can only see own appointments.
        Staff can see all appointments.
        """
        user = self.request.user
        if user.is_staff:
            return Appointment.objects.all()
        return Appointment.objects.filter(patient_id=user.id)

    def perform_create(self, serializer):
        """
        Set user as patient, and set constant price
        """
        user = self.request.user
        slot = serializer.validated_data["doctor_slot"]
        patient = serializer.validated_data.get("patient", user)

        serializer.save(
            patient=patient,
            booked_at=slot.start,
            price=slot.doctor.price_per_visit,
        )

    """
    Cancellation logic with validation and transaction
    """

    @extend_schema(
        summary="Mark appointment as Canceled",
        description=(
            "Changes the appointment status to CANCELED "
            "and charging 50% of price from balance if cancelled "
            "later than 24 hours before the visit."
            "Allowed for staff and users."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                description="Success",
                examples=[
                    OpenApiExample(
                        "Success response",
                        value={
                            "status": "Success",
                            "message": "Appointment marked as 'Cancelled'."
                            "Attempt to withdraw funds from the balance",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Bad Request",
                examples=[
                    OpenApiExample(
                        "Invalid status",
                        value={
                            "error": "Only BOOKED appointments can be marked as 'Cancelled'."
                        },
                    ),
                ],
            ),
            503: OpenApiResponse(
                description="Transaction failed / Server error",
                examples=[
                    OpenApiExample(
                        "Database error",
                        value={"error": "Transaction failed: Database connection lost"},
                    )
                ],
            ),
        },
        tags=["Appointments Management"],
    )
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

        try:
            with transaction.atomic():
                time_until_appointment = appointment.booked_at - timezone.now()
                appointment.status = appointment.Status.CANCELLED
                appointment.save()

            if time_until_appointment < timedelta(hours=24):
                payment = appointment.payments.filter(
                    payment_type=Payment.Type.CANCELLATION_FEE,
                    status=Payment.Status.PENDING,
                ).first()

                if not payment:
                    pass

                return Response(
                    {
                        "status": "Appointment cancelled",
                        "payment_url": payment.session_url,
                        "payment_id": payment.id,
                    }
                )

        except Exception as e:
            return Response(
                {"error": f"Status is CANCELLED, but payment failed: {str(e)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    """
    Completed mark logic with validation and transaction
    """

    @extend_schema(
        summary="Mark appointment as Completed",
        description=(
            "Changes the appointment status to COMPLETED"
            " and charging 100% of price from balance"
            "Allowed only for staff users."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                description="Success",
                examples=[
                    OpenApiExample(
                        "Success response",
                        value={
                            "status": "Success",
                            "message": "Appointment marked as 'Completed'."
                            "Attempt to withdraw funds from the balance",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Bad Request",
                examples=[
                    OpenApiExample(
                        "Invalid status",
                        value={
                            "error": "Only BOOKED appointments can be marked as 'No Show'."
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(description="Permission Denied (Admin only)"),
            503: OpenApiResponse(
                description="Server error / Service unavailable / Stripe error",
                examples=[
                    OpenApiExample(
                        "Database error",
                        value={"error": "Transaction failed: Database connection lost"},
                    )
                ],
            ),
        },
        tags=["Appointments Management"],
    )
    @action(
        methods=["POST"],
        detail=True,
        url_path="completed",
        permission_classes=[IsAdminUser],
    )
    def completed_appointment(self, request, pk=None):
        appointment = self.get_object()

        if appointment.status not in [
            appointment.Status.BOOKED,
            appointment.Status.COMPLETED,
        ]:
            return Response(
                {
                    "error": f"Cannot complete appointment from status: {appointment.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if appointment.status == appointment.Status.BOOKED:
                with transaction.atomic():
                    appointment.status = appointment.Status.COMPLETED
                    appointment.completed_at = timezone.now()
                    appointment.save()

            payment = appointment.payments.filter(
                payment_type=Payment.Type.CONSULTATION, status=Payment.Status.PENDING
            ).first()

            if not payment:
                pass

            return Response(
                {
                    "status": "Appointment completed",
                    "payment_url": payment.session_url,
                    "payment_id": payment.id,
                }
            )

        except Exception as e:
            return Response(
                {"error": f"Status is NO SHOW, but payment failed: {str(e)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    """
    No show mark logic with validation and transaction
    """

    @extend_schema(
        summary="Mark appointment as No-Show",
        description=(
            "Changes the appointment status to NO_SHOW and creates a penalty payment (120%). "
            "Allowed only for staff users. Can only be performed after the appointment start time."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                description="Success",
                examples=[
                    OpenApiExample(
                        "Success response",
                        value={
                            "status": "Success",
                            "message": "Appointment marked as 'No Show'. 120% penalty fee applied."
                            "Attempt to withdraw funds from the balance",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Bad Request",
                examples=[
                    OpenApiExample(
                        "Invalid status",
                        value={
                            "error": "Only BOOKED appointments can be marked as 'No Show'."
                        },
                    ),
                    OpenApiExample(
                        "Too early",
                        value={
                            "error": "You cannot mark as 'No Show' before the appointment time starts."
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(description="Permission Denied (Admin only)"),
            503: OpenApiResponse(
                description="Transaction failed / Server error",
                examples=[
                    OpenApiExample(
                        "Database error",
                        value={"error": "Transaction failed: Database connection lost"},
                    )
                ],
            ),
        },
        tags=["Appointments Management"],
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

        try:
            if appointment.status == appointment.Status.BOOKED:
                with transaction.atomic():
                    appointment.status = appointment.Status.NO_SHOW
                    appointment.save()

            payment = appointment.payments.filter(
                payment_type=Payment.Type.NO_SHOW_FEE, status=Payment.Status.PENDING
            ).first()

            if not payment:
                pass

            return Response(
                {
                    "status": "Appointment marked as no show",
                    "payment_url": payment.session_url,
                    "payment_id": payment.id,
                }
            )

        except Exception as e:
            return Response(
                {"error": f"Status is NO SHOW, but payment failed: {str(e)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    def _create_payment(self, appointment, payment_type):
        pass
