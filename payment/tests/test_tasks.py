from unittest.mock import patch, MagicMock

from django.utils import timezone

from payment.models import Payment
from payment.tasks import create_stripe_payment_task, sync_pending_payments
from payment.tests.base_set_up import BaseTestCaseModel
import datetime


class CreateStripePaymentTaskTests(BaseTestCaseModel):

    @patch("payment.tasks.process_appointment_payment")
    def test_create_stripe_payment_task_calls_service(self, mock_process):
        create_stripe_payment_task(
            self.appointment.id,
            Payment.Type.CONSULTATION
        )

        mock_process.assert_called_once_with(
            appointment=self.appointment,
            payment_type=Payment.Type.CONSULTATION,
        )

    @patch("payment.tasks.logger.error")
    def test_task_logs_error_if_appointment_missing(self, mock_logger):
        create_stripe_payment_task(999999, Payment.Type.CONSULTATION)

        mock_logger.assert_called()

    @patch("payment.tasks.process_appointment_payment")
    def test_task_retries_on_exception(self, mock_process):
        mock_process.side_effect = Exception("Boom")

        task = create_stripe_payment_task
        with self.assertRaises(Exception):
            task(self.appointment.id, Payment.Type.CONSULTATION)

        mock_process.assert_called_once()


class FakeStripeSession:
    def __init__(self, payment_status=None, status=None):
        self.payment_status = payment_status
        self.status = status


class SyncPendingPaymentsTests(BaseTestCaseModel):
    def setUp(self):
        super().setUp()
        self.old_time = timezone.now() - datetime.timedelta(hours=2)

    @patch("payment.tasks.stripe.checkout.Session.retrieve")
    def test_sync_marks_paid_when_stripe_paid(self, mock_retrieve):
        payment = Payment.objects.create(
            appointment=self.appointment,
            session_id="cs_123",
            money_to_pay=100,
            status=Payment.Status.PENDING,
            created_at=timezone.now() - datetime.timedelta(minutes=60),
        )

        Payment.objects.filter(id=payment.id).update(created_at=self.old_time)

        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_retrieve.return_value = mock_session

        sync_pending_payments()

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PAID)

    @patch("payment.tasks.stripe.checkout.Session.retrieve")
    def test_sync_marks_expired_when_stripe_expired(self, mock_retrieve):
        payment = Payment.objects.create(
            appointment=self.appointment,
            session_id="cs_456",
            money_to_pay=100,
            status=Payment.Status.PENDING,
        )
        Payment.objects.filter(id=payment.id).update(created_at=self.old_time)

        mock_session = MagicMock()
        mock_session.payment_status = "unpaid"
        mock_session.status = "expired"
        mock_retrieve.return_value = mock_session

        sync_pending_payments()

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.EXPIRED)

    @patch("payment.tasks.logger.warning")
    def test_sync_skips_payment_without_session(self, mock_logger):
        payment = Payment.objects.create(
            appointment=self.appointment,
            session_id="",
            money_to_pay=100,
            status=Payment.Status.PENDING,
        )
        Payment.objects.filter(id=payment.id).update(created_at=self.old_time)

        sync_pending_payments()

        mock_logger.assert_called()
