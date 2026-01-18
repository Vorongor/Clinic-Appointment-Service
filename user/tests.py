from datetime import datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from user.models import Patient
from appointment.models import Appointment
from payment.models import Payment

CREATE_USER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token_obtain_pair")


class UserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "first_name": "Ivan",
            "last_name": "Ivanov",
        }

    def test_create_user_success(self):
        res = self.client.post(CREATE_USER_URL, self.user_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=self.user_data["email"])
        self.assertTrue(user.check_password(self.user_data["password"]))
        self.assertEqual(user.first_name, self.user_data["first_name"])

    def test_obtain_token_success(self):
        get_user_model().objects.create_user(**self.user_data)

        payload = {
            "email": self.user_data["email"],
            "password": self.user_data["password"],
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_patient_profile_created_automatically(self):
        self.client.post(CREATE_USER_URL, self.user_data)
        user = get_user_model().objects.get(email=self.user_data["email"])
        self.assertTrue(hasattr(user, "patient_profile"))
        self.assertIsNotNone(user.patient_profile)

    def test_patient_deleted_when_user_deleted(self):
        self.client.post(CREATE_USER_URL, self.user_data)
        user = get_user_model().objects.get(email=self.user_data["email"])
        user_id = user.id
        user.delete()
        patient_exists = Patient.objects.filter(user_id=user_id).exists()
        self.assertFalse(patient_exists)


class PatientStatusTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="patient@test.com",
            password="password123",
            first_name="Ivan",
            last_name="Ivanov"
        )
        self.patient = self.user.patient_profile
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            time=datetime.now()
        )

    def test_total_unpaid_amount_calculation(self):
        Payment.objects.create(
            appointment=self.appointment,
            status=Payment.Status.PENDING,
            payment_type=Payment.Type.CONSULTATION,
            money_to_pay="500.00"
        )
        Payment.objects.create(
            appointment=self.appointment,
            status=Payment.Status.PENDING,
            payment_type=Payment.Type.CANCELLATION_FEE,
            money_to_pay="150.00"
        )
        self.assertEqual(float(self.patient.total_unpaid_amount), 650.00)

    def test_has_active_penalties_logic(self):
        self.assertFalse(self.patient.has_active_penalties)
        Payment.objects.create(
            appointment=self.appointment,
            status=Payment.Status.PENDING,
            payment_type=Payment.Type.NO_SHOW_FEE,
            money_to_pay="100.00"
        )
        self.assertTrue(self.patient.has_active_penalties)
        Payment.objects.create(
            appointment=self.appointment,
            status=Payment.Status.PAID,
            payment_type=Payment.Type.CANCELLATION_FEE,
            money_to_pay="100.00"
        )
        self.assertTrue(self.patient.has_active_penalties)
