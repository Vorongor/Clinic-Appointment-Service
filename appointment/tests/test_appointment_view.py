from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from unittest import TestCase

from appointment.models import Appointment
from appointment.serializers import AppointmentListSerializer

APPOINTMENT_URL = reverse("appointment:appointment-list")


class AuthenticatedAppointmentApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_get_only_user_appointments(self):
        pass

    def test_get_movie_detail(self) -> None:
        pass
