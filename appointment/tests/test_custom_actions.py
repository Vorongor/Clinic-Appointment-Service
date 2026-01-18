from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from appointment.models import Appointment
from doctor.models import Doctor, DoctorSlot
from payment.models import Payment

User = get_user_model()


class AppointmentActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.patient_user = User.objects.create_user(
            email="patient@example.com", password="password123"
        )
        self.other_patient = User.objects.create_user(
            email="victim@example.com", password="password123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )

        self.doctor = Doctor.objects.create(
            first_name="Gregory",
            last_name="House",
            price_per_visit=500.00,
        )

        self.future_start = timezone.now() + timezone.timedelta(days=1)
        self.slot = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=self.future_start,
            end=self.future_start + timezone.timedelta(minutes=30),
        )

        self.appointment = Appointment.objects.create(
            doctor_slot=self.slot,
            patient=self.patient_user,
            booked_at=self.future_start,
            price=self.doctor.price_per_visit,
            status="BOOKED",
        )

    @patch("payment.tasks.create_stripe_payment_task.delay")
    def test_cancel_appointment_action(self, mock_payment_task):
        """
        Checking:
        1. Status changes to CANCELLED.
        2. Calling task to create penalty payment (CANCELLATION_FEE).
        3. If we can use slot again after cancelling appointment.
        """

        self.client.force_authenticate(user=self.patient_user)

        url_cancel = reverse("appointment-cancel-appointment", args=[self.appointment.id])

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url_cancel)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CANCELLED)

        mock_payment_task.assert_called_with(
            self.appointment.id,
            Payment.Type.CANCELLATION_FEE
        )

        self.client.force_authenticate(user=self.other_patient)

        url_create = reverse("appointment-list")

        new_booking_data = {
            "doctor_slot": self.slot.id,
        }

        response_rebook = self.client.post(url_create, new_booking_data)

        self.assertEqual(
            response_rebook.status_code,
            status.HTTP_201_CREATED,
        )

        """
        Here we checking if we have 2 appointments with same slot
        One appointment is cancelled (It isn't deleted)
        Another is booked and active
        """
        active_appointments = Appointment.objects.filter(
            doctor_slot=self.slot,
            status=Appointment.Status.BOOKED,
        )
        self.assertEqual(active_appointments.count(), 1)
        self.assertEqual(active_appointments.first().patient, self.other_patient)

    @patch("payment.tasks.create_stripe_payment_task.delay")
    def test_completed_appointment_action(self, mock_payment_task):
        """
        Checking:
        1. Status changed to COMPLETED.
        2. Calling task to create payment (CONSULTATION) if we don't have it.
        """
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("appointment-completed-appointment", args=[self.appointment.id])

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

        mock_payment_task.assert_called_with(
            self.appointment.id,
            Payment.Type.CONSULTATION
        )

    @patch("payment.tasks.create_stripe_payment_task.delay")
    def test_no_show_fail_if_future(self, mock_payment_task):
        """
        Checking that we can't mark future appointment as no-show
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("appointment-no-show-appointment", args=[self.appointment.id])

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

        self.appointment.refresh_from_db()
        self.assertNotEqual(self.appointment.status, Appointment.Status.NO_SHOW)

        # Task shouldn't be called
        mock_payment_task.assert_not_called()

    @patch("payment.tasks.create_stripe_payment_task.delay")
    def test_no_show_success_if_past(self, mock_payment_task):
        """
        Checking success no-show action with payment creation
        """
        past_time = timezone.now() - timezone.timedelta(days=1)
        past_slot = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=past_time,
            end=past_time + timezone.timedelta(minutes=30),
        )
        past_appointment = Appointment.objects.create(
            doctor_slot=past_slot,
            patient=self.patient_user,
        )

        self.client.force_authenticate(user=self.admin_user)
        url = reverse("appointment-no-show-appointment", args=[past_appointment.id])

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        past_appointment.refresh_from_db()
        self.assertEqual(past_appointment.status, Appointment.Status.NO_SHOW)

        mock_payment_task.assert_called_with(
            past_appointment.id,
            Payment.Type.NO_SHOW_FEE
        )
