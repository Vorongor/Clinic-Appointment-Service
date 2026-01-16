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


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = [AllowAny,]
    authentication_classes = []

    def get_authenticators(self):
        return []

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except stripe.error.SignatureVerificationError as e:
            return HttpResponse(content="Invalid signature", status=400)
        except ValueError as e:
            return HttpResponse(content="Invalid payload", status=400)

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']

            payment = Payment.objects.filter(session_id=session.id).first()
            if payment:
                payment.status = Payment.Status.PAID
                payment.save()

                # TODO Send notification payment success
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

    # @extend_schema(
    #     summary="Stripe success redirect",
    #     description="Checks Stripe Checkout Session by session_id and marks "
    #                 "Payment as PAID if payment_status == 'paid'.",
    #     parameters=[
    #         OpenApiParameter(
    #             name="session_id",
    #             required=True,
    #             type=str,
    #             location=OpenApiParameter.QUERY,
    #             description="Stripe Checkout Session id (cs_...).",
    #         )
    #     ],
    #     responses={200: None, 400: None, 404: None, 500: None},
    # )
    # @action(detail=False, methods=["get"], url_path="success",
    #         permission_classes=[AllowAny])
    # def success(self, request):
    #     session_id = request.query_params.get("session_id")
    #     if not session_id:
    #         return Response(
    #             {"detail": "Missing query param: session_id"},
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )
    #
    #     try:
    #         payment = Payment.objects.select_related(
    #             "appointment", "appointment__patient"
    #         ).get(session_id=session_id)
    #     except Payment.DoesNotExist:
    #         return Response(
    #             {"detail": "Payment not found for this session_id"},
    #             status=status.HTTP_404_NOT_FOUND,
    #         )
    #
    #     if not getattr(settings, "STRIPE_SECRET_KEY", None):
    #         return Response(
    #             {
    #                 "detail": "Stripe is not configured "
    #                           "(STRIPE_SECRET_KEY missing)"},
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         )
    #
    #     stripe.api_key = settings.STRIPE_SECRET_KEY
    #
    #     try:
    #         session = stripe.checkout.Session.retrieve(session_id)
    #     except stripe.error.StripeError as e:
    #         return Response(
    #             {"detail": "Stripe error while retrieving session",
    #              "error": str(e)},
    #             status=status.HTTP_502_BAD_GATEWAY,
    #         )
    #
    #     if getattr(session, "payment_status", None) != "paid":
    #         return Response(
    #             {
    #                 "detail": "Payment not completed yet",
    #                 "stripe_payment_status": getattr(session, "payment_status",
    #                                                  None),
    #                 "stripe_status": getattr(session, "status", None),
    #             },
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )
    #
    #     if payment.status != Payment.Status.PAID:
    #         payment.status = Payment.Status.PAID
    #         payment.save(update_fields=["status"])
    #
    #     return Response(
    #         {
    #             "detail": "Payment confirmed",
    #             "payment_id": payment.id,
    #             "status": payment.status,
    #         },
    #         status=status.HTTP_200_OK,
    #     )

    # @extend_schema(
    #     summary="Stripe cancel redirect",
    #     description="Returns a message that payment can be completed later.",
    #     responses={200: None},
    # )
    # @action(detail=False, methods=["get"], url_path="cancel",
    #         permission_classes=[AllowAny])
    # def cancel(self, request):
    #     return Response(
    #         {
    #             "detail": "Payment was cancelled/paused. "
    #                       "You can try again later."},
    #         status=status.HTTP_200_OK,
    #     )




