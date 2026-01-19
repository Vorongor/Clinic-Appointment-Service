import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, PropertyMock

from django.utils import timezone
from payment.models import Payment
from payment.tests.base_set_up import BaseTestCaseModel
from payment.services.logic import (
    calculate_payment_amount,
    process_appointment_payment,
    renew_payment_session
)


class RefactoredLogicTest(BaseTestCaseModel):

    def test_calculate_cancellation_fee_less_than_24h(self):
        time_diff = datetime.timedelta(hours=5)
        price = calculate_payment_amount(
            self.appointment,
            Payment.Type.CANCELLATION_FEE,
            time_diff=time_diff
        )
        self.assertEqual(price, Decimal("5.0"))

    def test_calculate_payment_with_user_penalty(self):
        with patch.object(
                type(self.appointment.patient),
                "has_penalty",
                new_callable=PropertyMock
        ) as mock_penalty:
            mock_penalty.return_value = Decimal("5.0")

            price = calculate_payment_amount(
                self.appointment,
                Payment.Type.CONSULTATION
            )

            self.assertEqual(price, Decimal("15.0"))

        price = calculate_payment_amount(
            self.appointment,
            Payment.Type.CONSULTATION
        )

        self.assertEqual(price, Decimal("10.0"))

    @patch("payment.services.logic.create_checkout_session")
    @patch("stripe.checkout.Session.retrieve")
    def test_renew_payment_already_paid_locally(self, mock_retrieve,
                                                mock_create):
        payment = Payment.objects.create(
            appointment=self.appointment,
            money_to_pay=Decimal("10.0"),
            status=Payment.Status.PAID
        )
        with self.assertRaises(ValueError) as cm:
            renew_payment_session(payment)
        self.assertEqual(str(cm.exception), "Paid payments can't be renewed")

    @patch("payment.services.logic.create_checkout_session")
    @patch("stripe.checkout.Session.retrieve")
    def test_renew_payment_updates_status_if_paid_on_stripe(self,
                                                            mock_retrieve,
                                                            mock_create):
        payment = Payment.objects.create(
            appointment=self.appointment,
            session_id="old_sess",
            money_to_pay=Decimal("10.0"),
            status=Payment.Status.PENDING
        )
        mock_stripe_session = MagicMock()
        mock_stripe_session.payment_status = "paid"
        mock_retrieve.return_value = mock_stripe_session

        renew_payment_session(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PAID)

    @patch("payment.services.logic.create_checkout_session")
    @patch("stripe.checkout.Session.expire")
    def test_process_consultation_creates_payment(self, mock_expire,
                                                  mock_create):
        mock_session = MagicMock(id="sess_new", url="https://stripe.com/new")
        mock_create.return_value = mock_session

        payment = process_appointment_payment(self.appointment,
                                              Payment.Type.CONSULTATION)

        self.assertEqual(payment.session_id, "sess_new")
        self.assertEqual(payment.payment_type, Payment.Type.CONSULTATION)
        self.assertEqual(Payment.objects.count(), 1)

    @patch("payment.services.logic.make_refund")
    def test_handle_cancellation_long_term_refunds(self, mock_refund):
        Payment.objects.create(
            appointment=self.appointment,
            money_to_pay=Decimal("10.0"),
            status=Payment.Status.PAID,
            stripe_payment_intent_id="pi_123"
        )

        self.appointment.booked_at = timezone.now() + datetime.timedelta(
            days=2)
        self.appointment.save()

        process_appointment_payment(self.appointment,
                                    Payment.Type.CANCELLATION_FEE)

        mock_refund.assert_called_once()
        args, kwargs = mock_refund.call_args
        self.assertEqual(kwargs['percentage'], 100)

    @patch("stripe.Refund.create")
    @patch("stripe.checkout.Session.retrieve")
    def test_make_refund_logic(self, mock_retrieve, mock_refund_create):
        payment = Payment.objects.create(
            appointment=self.appointment,
            money_to_pay=Decimal("10.0"),
            status=Payment.Status.PAID,
            stripe_payment_intent_id="pi_123"
        )

        from payment.services.logic import make_refund
        success = make_refund(payment, percentage=50)

        self.assertTrue(success)
        mock_refund_create.assert_called_with(
            payment_intent="pi_123",
            amount=500
        )
        self.assertEqual(payment.status, Payment.Status.PARTIALLY_REFUNDED)