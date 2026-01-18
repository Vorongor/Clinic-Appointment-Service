from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample

from payment.models import Payment


@extend_schema_serializer(
    description=(
        "Payment object created for an appointment.\n\n"
        "Payments are created for:\n"
        "- consultation (after appointment completion)\n"
        "- cancellation fee (late cancellation)\n"
        "- no-show fee\n\n"
        "Patients can access only payments linked to their own appointments."
    ),
    examples=[
        OpenApiExample(
            "Pending consultation payment",
            value={
                "id": 12,
                "status": "PENDING",
                "payment_type": "CONSULTATION",
                "appointment": 34,
                "session_url": "https://checkout.stripe.com/c/pay/cs_test_...",
                "session_id": "cs_test_...",
                "money_to_pay": "25.00",
                "created_at": "2026-01-18T12:34:56Z",
            },
            response_only=True,
        ),
        OpenApiExample(
            "Expired payment session (needs renew)",
            value={
                "id": 13,
                "status": "EXPIRED",
                "payment_type": "NO_SHOW_FEE",
                "appointment": 35,
                "session_url": "https://checkout.stripe.com/c/pay/cs_test_old...",
                "session_id": "cs_test_old...",
                "money_to_pay": "30.00",
                "created_at": "2026-01-17T09:10:11Z",
            },
            response_only=True,
        ),
        OpenApiExample(
            "Paid payment",
            value={
                "id": 14,
                "status": "PAID",
                "payment_type": "CANCELLATION_FEE",
                "appointment": 36,
                "session_url": "https://checkout.stripe.com/c/pay/cs_test_...",
                "session_id": "cs_test_...",
                "money_to_pay": "10.00",
                "created_at": "2026-01-16T08:00:00Z",
            },
            response_only=True,
        ),
    ],
)
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "status",
            "payment_type",
            "appointment",
            "session_url",
            "session_id",
            "money_to_pay",
            "created_at",
        )
        read_only_fields = fields
        extra_kwargs = {
            "status": {
                "help_text": "Payment status: PENDING, PAID, or EXPIRED.",
            },
            "payment_type": {
                "help_text": "Type of payment:"
                             "CONSULTATION, CANCELLATION_FEE, or NO_SHOW_FEE.",
            },
            "appointment": {
                "help_text": "Related Appointment ID.",
            },
            "session_url": {
                "help_text": "Stripe Checkout URL to complete payment"
                             "(usually present when status=PENDING).",
            },
            "session_id": {
                "help_text": "Stripe Checkout Session ID.",
            },
            "money_to_pay": {
                "help_text": "Amount in USD that should be paid for this payment.",
            },
            "created_at": {
                "help_text": "Timestamp when this Payment record was created.",
            },
        }
