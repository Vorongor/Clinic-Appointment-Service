from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from appointment.models import Appointment
from doctor.models import DoctorSlot, Doctor

User = get_user_model()


class AppointmentCreateAPITests(APITestCase):
    """
    Test for booking appointment (POST /api/appointments/).
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("appointment-list")

        self.patient_user = User.objects.create_user(
            email="patient@example.com", password="password123"
        )
        self.other_patient = User.objects.create_user(
            email="victim@example.com", password="password123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.doctor_user = User.objects.create_user(
            email="doc@example.com", password="docpass"
        )

        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
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

    def test_patient_can_create_appointment_for_self(self):
        """
        Patient booking for himself
        """
        self.client.force_authenticate(user=self.patient_user)

        payload = {"doctor_slot": self.slot.id}

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        appointment = Appointment.objects.get(id=response.data["id"])
        self.assertEqual(appointment.patient, self.patient_user)
        self.assertEqual(appointment.doctor_slot, self.slot)
        self.assertEqual(appointment.price, 500.00)

    def test_patient_cannot_book_for_another_user(self):
        """
        Patient don't have permission to book appointment for another user.
        """
        self.client.force_authenticate(user=self.patient_user)

        payload = {
            "doctor_slot": self.slot.id,
            "patient": self.other_patient.id,
        }

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        appointment = Appointment.objects.get(id=response.data["id"])

        self.assertEqual(appointment.patient, self.patient_user)
        self.assertNotEqual(appointment.patient, self.other_patient)

    def test_admin_can_book_for_any_patient(self):
        """
        Admin can book appointment for every user
        """
        self.client.force_authenticate(user=self.admin_user)

        payload = {
            "doctor_slot": self.slot.id,
            "patient": self.other_patient.id,
        }

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        appointment = Appointment.objects.get(id=response.data["id"])
        self.assertEqual(appointment.patient, self.other_patient)

    def test_cannot_book_already_taken_slot(self):
        """
        Can't book appointment for busy slot
        """
        Appointment.objects.create(
            doctor_slot=self.slot,
            patient=self.patient_user,
            booked_at=self.slot.start,
            price=self.doctor.price_per_visit,
            status="BOOKED",
        )

        self.client.force_authenticate(user=self.patient_user)
        payload = {"doctor_slot": self.slot.id}

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
