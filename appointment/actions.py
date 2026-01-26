from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from drf_spectacular.utils import OpenApiResponse, OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response


class AppointmentActionsMixin:
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
                            "message": "Appointment cancelled.",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Bad Request",
                examples=[
                    OpenApiExample(
                        # fmt: off
                            "Invalid status",
                            value={
                                "error":
                                    "You can't cancel appointment "
                                    "with this status"
                            },
                        # fmt: on
                    ),
                ],
            ),
            503: OpenApiResponse(
                description="Server error",
                examples=[
                    OpenApiExample(
                        "Database error",
                        value={"error": "Database connection lost"},
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
                {"error": "You can't cancel appointment with this status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                appointment.status = appointment.Status.CANCELLED
                appointment.save()

            return Response(
                {"message": "Appointment cancelled"}, status=status.HTTP_200_OK
            )

        except ValidationError as e:
            return Response(
                {"error": e.message_dict}, status=status.HTTP_400_BAD_REQUEST
            )

        except IntegrityError:
            return Response(
                {
                    "error": "This action violates database integrity "
                    "(possibly duplicate)."
                },
                status=status.HTTP_409_CONFLICT,
            )

        except DatabaseError:
            return Response(
                {
                    "error": "Database is currently unavailable. "
                    "Please try again later."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    """
    Completed mark logic with validation
    """

    @extend_schema(
        summary="Mark appointment as Completed",
        description=(
            "Changes the appointment status to COMPLETED "
            "and charging 100% of price from balance."
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
                            "message": "Appointment completed",
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
                            "error": "Cannot complete appointment "
                            "from status: {appointment.status}"
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(description="Permission Denied (Admin only)"),
            503: OpenApiResponse(
                description="Server error",
                examples=[
                    OpenApiExample(
                        "Database error",
                        value={"error": "Database connection lost"},
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

        if appointment.status != appointment.Status.BOOKED:
            return Response(
                {
                    "error": f"Cannot complete appointment "
                    f"from status: {appointment.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                appointment.status = appointment.Status.COMPLETED
                appointment.completed_at = timezone.now()
                appointment.save()

            return Response(
                {"message": "Appointment completed"}, status=status.HTTP_200_OK
            )

        except ValidationError as e:
            return Response(
                {"error": e.message_dict}, status=status.HTTP_400_BAD_REQUEST
            )

        except IntegrityError:
            return Response(
                {
                    "error": "This action violates database integrity "
                    "(possibly duplicate)."
                },
                status=status.HTTP_409_CONFLICT,
            )

        except DatabaseError:
            return Response(
                {
                    "error": "Database is currently unavailable. "
                    "Please try again later."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    """
    No show mark logic with validation
    """

    @extend_schema(
        summary="Mark appointment as No-Show",
        description=(
            "Changes the appointment status to NO_SHOW "
            "and creates a penalty payment (120%). "
            "Allowed only for staff users. Can only be "
            "performed after the appointment start time."
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
                            "message": "Appointment marked as 'No Show'",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Bad Request",
                examples=[
                    OpenApiExample(
                        # fmt: off
                        "Invalid status",
                        value={
                            "error":
                                "You can't mark this appointment "
                                "as 'No show'"
                        },
                        # fmt: on
                    ),
                    OpenApiExample(
                        "Too early",
                        value={
                            "error": "You cannot mark as 'No Show' "
                            "before the appointment time starts."
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(description="Permission Denied (Admin only)"),
            503: OpenApiResponse(
                description="Server error",
                examples=[
                    OpenApiExample(
                        "Database error",
                        value={"error": "Database connection lost"},
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
                {"error": "You can't mark this appointment as 'No show'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if appointment.booked_at > timezone.now():
            return Response(
                {
                    "error": "You cannot mark as 'No Show' "
                    "before the appointment time starts."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                appointment.status = appointment.Status.NO_SHOW
                appointment.save()

            return Response(
                "Appointment marked as 'No Show'", status=status.HTTP_200_OK
            )

        except ValidationError as e:
            return Response(
                {"error": e.message_dict}, status=status.HTTP_400_BAD_REQUEST
            )

        except IntegrityError:
            return Response(
                {
                    "error": "This action violates database integrity "
                    "(possibly duplicate)."
                },
                status=status.HTTP_409_CONFLICT,
            )

        except DatabaseError:
            return Response(
                {
                    "error": "Database is currently unavailable. "
                    "Please try again later."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
