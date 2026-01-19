import stripe

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)

from payment.models import Payment
from payment.serializers import PaymentSerializer
from payment.services.logic import renew_payment_session


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema(
    tags=["Payments"],
    operation_id="payments_stripe_webhook",
    summary="Stripe webhook receiver",
    description=(
        "Receives Stripe webhook events and updates Payment status.\n\n"
        "This endpoint is called by Stripe (server-to-server). "
        "It validates the `Stripe-Signature` header and processes events like:\n"
        "- `checkout.session.completed`\n\n"
        "Authentication is disabled here because Stripe signs requests."
    ),
    parameters=[
        OpenApiParameter(
            name="Stripe-Signature",
            required=True,
            type=str,
            location=OpenApiParameter.HEADER,
            description="Signature header used to validate Stripe webhook payload.",
        )
    ],
    request=OpenApiTypes.OBJECT,
    responses={
        200: OpenApiResponse(description="Event accepted"),
        400: OpenApiResponse(description="Invalid payload or invalid signature"),
    },
    auth=[],
)
class StripeWebhookView(APIView):
    permission_classes = [AllowAny, ]
    authentication_classes = []

    def get_authenticators(self):
        return []

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except stripe.error.SignatureVerificationError:
            return HttpResponse(content="Invalid signature", status=400)
        except ValueError:
            return HttpResponse(content="Invalid payload", status=400)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]

            payment = Payment.objects.filter(session_id=session.id).first()
            if payment:
                payment.status = Payment.Status.PAID
                payment.stripe_payment_intent_id = session.payment_intent
                payment.save()

                appointment = payment.appointment
                appointment.status = "BOOKED"
                appointment.save()

        return HttpResponse(status=200)


@extend_schema_view(
    list=extend_schema(
        operation_id="payments_list",
        summary="List payments",
        description=(
            "Returns payments ordered by newest first.\n\n"
            "- **Patients** see only payments for their own appointments.\n"
            "- **Staff** users see all payments."
        ),
        responses={200: PaymentSerializer(many=True)},
    ),
    retrieve=extend_schema(
        operation_id="payments_retrieve",
        summary="Get payment details",
        description=(
            "Returns a single payment by id.\n\n"
            "Patients can access only payments linked to their own appointments."
        ),
        responses={200: PaymentSerializer},
    ),
)
@extend_schema(tags=["Payments"])
class PaymentViewSet(ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related(
            "appointment",
            "appointment__patient"
        )
        if user.is_staff:
            return qs
        return qs.filter(appointment__patient=user)

    @extend_schema(
        operation_id="payments_stripe_success",
        summary="Stripe success redirect",
        description=(
                "Endpoint used as `success_url` for Stripe Checkout.\n\n"
                "Looks up Payment by `session_id`"
                "and returns a human-readable message "
                "plus current payment status and appointment id."
        ),
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Stripe Checkout Session ID returned by Stripe.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Payment found for given session_id.",
                examples=[
                    OpenApiExample(
                        "Success response",
                        value={
                            "detail":
                                "Thank you for your payment!"
                                "Your appointment is being processed.",
                            "payment_status": "PAID",
                            "appointment_id": 34,
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(description="session_id is missing"),
            404: OpenApiResponse(description="Payment not found"),
        },
        auth=[],
    )
    @action(detail=False, methods=["get"], url_path="success",
            permission_classes=[AllowAny])
    def success(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"detail": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment = Payment.objects.filter(session_id=session_id).first()
        if not payment:
            return Response(
                {"detail": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "detail": "Thank you for your payment! "
                          "Your appointment is being processed.",
                "payment_status": payment.status,
                "appointment_id": payment.appointment.id
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="payments_stripe_cancel",
        summary="Stripe cancel redirect",
        description=(
                "Endpoint used as `cancel_url` for Stripe Checkout.\n\n"
                "Returns a message that payment can be completed later."
        ),
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Optional Stripe Checkout Session ID.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Cancel message.",
                examples=[
                    OpenApiExample(
                        "Cancel response",
                        value={
                            "detail":
                                "Payment was cancelled."
                                "You can complete it later in your dashboard."
                        },
                        response_only=True,
                    )
                ],
            ),
        },
        auth=[],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="cancel",
        permission_classes=[AllowAny]
    )
    def cancel(self, request):
        # TODO TRIGGER TASK STUB: appointment_cancel_update
        session_id = request.query_params.get("session_id")

        if session_id:
            payment = Payment.objects.filter(session_id=session_id).first()
            if payment:
                print(
                    f"DEBUG: Triggering task appointment_cancel_update for "
                    f"Appointment {payment.appointment.id}")

        # TODO TRIGGER TASK STUB: appointment_cancel_update
        return Response(
            {
                "detail": "Payment was cancelled. "
                          "You can complete it later in your dashboard."
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="payments_renew_session",
        summary="Renew Stripe Checkout session",
        description=(
                "Creates a new Stripe Checkout session for an existing Payment.\n\n"
                "Use this when the previous session expired"
                "or the user lost the link.\n"
                "- If the Stripe session is still open,"
                "the current session_url is returned.\n"
                "- Paid payments can't be renewed."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=PaymentSerializer,
                description="Renewed payment session details.",
                examples=[
                    OpenApiExample(
                        "Renew response",
                        value={
                            "id": 13,
                            "status": "PENDING",
                            "payment_type": "NO_SHOW_FEE",
                            "appointment": 35,
                            "session_url":
                                "https://checkout.stripe.com/c/pay/cs_test_new...",
                            "session_id": "cs_test_new...",
                            "money_to_pay": "30.00",
                            "created_at": "2026-01-17T09:10:11Z",
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Cannot renew (paid or nothing to pay)"
            ),
            404: OpenApiResponse(description="Payment not found / not accessible"),
        },
    )
    @action(detail=True, methods=["post"], url_path="renew")
    def renew(self, request, pk=None):
        payment = self.get_object()

        try:
            payment = renew_payment_session(payment)
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as err:
            return Response(
                {"detail": f"Failed to renew payment session: {err}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)
