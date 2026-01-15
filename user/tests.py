from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

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
            "password": self.user_data["password"]
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_patient_profile_created_automatically(self):
        self.client.post(CREATE_USER_URL, self.user_data)
        user = get_user_model().objects.get(email=self.user_data["email"])
        self.assertTrue(hasattr(user, 'patient_profile'))
        self.assertIsNotNone(user.patient_profile)

    def test_user_deleted_when_patient_deleted(self):
        res = self.client.post(CREATE_USER_URL, self.user_data)
        user = get_user_model().objects.get(email=self.user_data["email"])
        patient = user.patient_profile
        patient.delete()
        user_exists = get_user_model().objects.filter(email=self.user_data["email"]).exists()
        self.assertFalse(user_exists)
