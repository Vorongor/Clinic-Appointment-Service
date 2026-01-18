import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient

from appointment.models import Appointment
from doctor.models import DoctorSlot, Doctor
from payment.models import Payment
from specializations.models import Specialization


class FakeSession:
    """Helper class to mimic Stripe session object"""
    def __init__(self, id):
        self.id = id


class StripeWebhookTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.start_time = timezone.make_aware(
            datetime.datetime(2026, 1, 10, 8, 0, 0))
        self.booked_time = self.start_time

        self.patient = get_user_model().objects.create_user(
            email="test@patient.com",
            password="1Qazcde3",
            first_name="test",
            last_name="test",
        )

        self.specialization = Specialization.objects.create(
            name="Test specialization",
            code="1234-test",
            description="Test specialization",
        )

        self.doctor = Doctor.objects.create(
            first_name="Test Doctor",
            last_name="Test Doctor",
            price_per_visit=Decimal("10.0"),
        )
        self.doctor.specializations.add(self.specialization)

        self.doctor_slot = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=self.start_time,
            end=self.start_time + datetime.timedelta(minutes=30),
        )

        self.appointment = Appointment.objects.create(
            doctor_slot=self.doctor_slot,
            patient=self.patient,
            booked_at=self.booked_time,
            price=self.doctor.price_per_visit
        )

        self.payment = Payment.objects.create(
            appointment=self.appointment,
            session_id="cs_test_123",
            money_to_pay=100,
            status=Payment.Status.PENDING
        )

        self.url = reverse("stripe-webhook")

    @patch("stripe.Webhook.construct_event")
    def test_webhook_checkout_session_completed(self, mock_construct):
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": FakeSession("cs_test_123")
            }
        }

        response = self.client.post(
            self.url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="fake_signature"
        )

        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.appointment.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.appointment.status, "BOOKED")

    @patch("stripe.Webhook.construct_event")
    def test_webhook_invalid_signature(self, mock_construct):
        import stripe

        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "msg",
            "sig"
        )

        response = self.client.post(
            self.url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid signature", response.content.decode())

    def test_success_endpoint_valid_session(self):
        url = reverse("payment-success")

        response = self.client.get(
            f"{url}?session_id={self.payment.session_id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["payment_status"],
            Payment.Status.PENDING
        )

    def test_success_endpoint_invalid_session(self):
        url = reverse("payment-success")

        response = self.client.get(f"{url}?session_id=non_existent")

        self.assertEqual(response.status_code, 404)
