from decimal import Decimal
from unittest.mock import patch
from datetime import timedelta


from payment.models import Payment
from payment.services.logic import process_appointment_payment
from payment.tests.base_set_up import BaseTestCaseModel


class PaymentServiceFreeCancellationTest(BaseTestCaseModel):
    @patch("payment.services.logic.create_checkout_session")
    @patch("stripe.checkout.Session.expire")
    @patch("django.utils.timezone.now")
    def test_free_cancellation_more_than_24h(
            self,
            mock_now,
            mock_stripe_expire,
            mock_create_session
    ):
        mock_now.return_value = self.booked_time - timedelta(days=5)

        existing_payment = Payment.objects.create(
            appointment=self.appointment,
            session_id="sess_to_expire",
            money_to_pay=Decimal("10.0"),
            payment_type=Payment.Type.CANCELLATION_FEE,
            status=Payment.Status.PENDING
        )

        result = process_appointment_payment(
            self.appointment,
            Payment.Type.CANCELLATION_FEE
        )

        mock_stripe_expire.assert_called_with("sess_to_expire")

        mock_create_session.assert_not_called()

        existing_payment.refresh_from_db()
        self.assertEqual(existing_payment.status, Payment.Status.EXPIRED)
        self.assertEqual(existing_payment.money_to_pay, Decimal("0.0"))

        self.assertEqual(result.id, existing_payment.id)
