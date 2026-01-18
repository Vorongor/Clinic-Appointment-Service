import stripe
from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter

from payment.models import Payment
from payment.serializers import PaymentSerializer


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema(tags=["Payments"])
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
                payment.save()

                appointment = payment.appointment
                appointment.status = "BOOKED"
                appointment.save()

        return HttpResponse(status=200)


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
        summary="Stripe success redirect",
        description="Handles user redirection after successful payment. "
                    "Triggers background tasks.",
        parameters=[
            OpenApiParameter(name="session_id", required=True, type=str,
                             location=OpenApiParameter.QUERY)
        ],
        responses={200: None, 400: None, 404: None},
    )
    @action(detail=False, methods=["get"], url_path="success",
            permission_classes=[AllowAny])
    def success(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"detail": "session_id is required"},
                            status=status.HTTP_400_BAD_REQUEST)

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
        summary="Stripe cancel redirect",
        description="Handles user redirection when they "
                    "cancel the payment process.",
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY
            )
        ],
        responses={200: None},
    )
    @action(detail=False, methods=["get"], url_path="cancel",
            permission_classes=[AllowAny])
    def cancel(self, request):
        session_id = request.query_params.get("session_id")

        if session_id:
            payment = Payment.objects.filter(session_id=session_id).first()
            if payment:
                print(
                    f"DEBUG: Triggering task appointment_cancel_update for "
                    f"Appointment {payment.appointment.id}")

        return Response(
            {
                "detail": "Payment was cancelled. "
                          "You can complete it later in your dashboard."
            },
            status=status.HTTP_200_OK,
        )
