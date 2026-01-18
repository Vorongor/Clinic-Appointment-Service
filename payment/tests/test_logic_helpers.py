import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from payment.models import Payment
from payment.tests.base_set_up import BaseTestCaseModel
from payment.services.logic import (
    calculate_payment_amount,
    process_appointment_payment
)


class LogicHelpersTest(BaseTestCaseModel):

    def test_calculate_payment_amount_for_consultation(self):
        consultation_price = calculate_payment_amount(
            appointment=self.appointment,
            payment_type=Payment.Type.CONSULTATION
        )
        self.assertEqual(consultation_price, Decimal("10.0"))

    def test_calculate_cancellation_fee_less_than_24h(self):
        mock_now = self.booked_time - datetime.timedelta(hours=5)

        from unittest.mock import patch
        with patch("django.utils.timezone.now", return_value=mock_now):
            price = calculate_payment_amount(
                self.appointment,
                Payment.Type.CANCELLATION_FEE
            )
            self.assertEqual(price, Decimal("5.0"))

    def test_calculate_cancellation_fee_more_than_24h(self):
        mock_now = self.booked_time - datetime.timedelta(days=2)

        from unittest.mock import patch
        with patch('django.utils.timezone.now', return_value=mock_now):
            price = calculate_payment_amount(
                self.appointment,
                Payment.Type.CANCELLATION_FEE
            )
            self.assertEqual(price, Decimal("0.0"))

    def test_calculate_no_show_fee(self):
        no_show_price = calculate_payment_amount(
            appointment=self.appointment,
            payment_type=Payment.Type.NO_SHOW_FEE
        )
        self.assertEqual(no_show_price, Decimal("12.0"))

    @patch("payment.services.logic.create_checkout_session")
    @patch("stripe.checkout.Session.expire")
    def test_process_new_payment_creation(
            self,
            mock_stripe_expire,
            mock_create_session
    ):
        mock_session = MagicMock()
        mock_session.id = "sess_123"
        mock_session.url = "https://stripe.com/pay"
        mock_create_session.return_value = mock_session

        payment = process_appointment_payment(
            self.appointment,
            Payment.Type.CONSULTATION
        )

        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(payment.session_id, "sess_123")
        self.assertEqual(payment.money_to_pay, self.appointment.price)
        mock_create_session.assert_called_once()

    @patch("payment.services.logic.create_checkout_session")
    @patch("stripe.checkout.Session.expire")
    def test_process_update_existing_payment(
            self,
            mock_stripe_expire,
            mock_create_session
    ):
        Payment.objects.create(
            appointment=self.appointment,
            session_id="old_id",
            money_to_pay=Decimal("10.0"),
            payment_type=Payment.Type.CONSULTATION,
            status=Payment.Status.PENDING
        )

        mock_session = MagicMock()
        mock_session.id = "new_sess_123"
        mock_session.url = "https://checkout.stripe.com/pay/new"
        mock_create_session.return_value = mock_session

        payment = process_appointment_payment(
            self.appointment,
            Payment.Type.NO_SHOW_FEE
        )

        mock_stripe_expire.assert_called_with("old_id")
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(payment.session_id, "new_sess_123")
        self.assertEqual(payment.payment_type, Payment.Type.NO_SHOW_FEE)
