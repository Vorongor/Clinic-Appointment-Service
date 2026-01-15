from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from ..models import Doctor, DoctorSlot
from ..serializers import DoctorSlotSerializer


class DoctorSlotTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="doc@example.com", password="pass"
        )
        self.doctor = Doctor.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            price_per_visit=100
        )

    def test_str_representation(self):
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        slot = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=start,
            end=end
        )
        s = str(slot)
        self.assertIn(f"Slot #{slot.id}", s)
        self.assertIn("Doctor - John Doe", s)
        self.assertIn(str(start), s)
        self.assertIn(str(end), s)

    def test_serializer_rejects_start_after_end(self):
        start = timezone.now()
        end = start - timezone.timedelta(hours=1)
        data = {"doctor": self.doctor.id, "start": start, "end": end}
        serializer = DoctorSlotSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("start must be before end", str(serializer.errors))

    def test_serializer_accepts_valid_data_and_creates(self):
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        data = {"doctor": self.doctor.id, "start": start, "end": end}
        serializer = DoctorSlotSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        obj = serializer.save()
        self.assertIsInstance(obj, DoctorSlot)
        self.assertEqual(DoctorSlot.objects.count(), 1)

    def test_unique_together_constraint(self):
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        DoctorSlot.objects.create(doctor=self.doctor, start=start, end=end)
        with self.assertRaises(IntegrityError):
            DoctorSlot.objects.create(doctor=self.doctor, start=start, end=end)

    def test_ordering_by_start(self):
        now = timezone.now()
        later = now + timezone.timedelta(hours=2)
        earlier = now - timezone.timedelta(hours=2)
        s1 = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=later,
            end=later+timezone.timedelta(hours=1)
        )
        s2 = DoctorSlot.objects.create(
            doctor=self.doctor,
            start=earlier,
            end=earlier+timezone.timedelta(hours=1)
        )
        qs = list(DoctorSlot.objects.all())
        self.assertEqual(qs, [s2, s1])


class DoctorSlotBulkCreateAPITests(APITestCase):
    """
    Tests for POST /api/doctors/<id>/slots/ endpoint.
    Bulk create slots for a doctor.
    """

    def setUp(self):
        User = get_user_model()
        # Create admin user for POST requests
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass"
        )
        # Create regular user (doctor)
        self.doctor_user = User.objects.create_user(
            email="doctor@example.com",
            password="docpass"
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            first_name="Jane",
            last_name="Smith",
            price_per_visit=150
        )
        self.client = APIClient()
        # Nested route: /api/doctors/<pk>/slots/
        self.url = f"/api/doctors/{self.doctor.pk}/slots/"

    def test_bulk_create_single_slot_as_list(self):
        """POST with list containing one slot creates it successfully."""
        self.client.force_authenticate(user=self.admin_user)
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        data = [
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
            }
        ]
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["start"], start.isoformat())
        self.assertEqual(response.data[0]["end"], end.isoformat())
        self.assertEqual(DoctorSlot.objects.count(), 1)

    def test_bulk_create_multiple_slots(self):
        """POST with list of multiple slots creates all of them."""
        self.client.force_authenticate(user=self.admin_user)
        now = timezone.now()
        data = [
            {
                "start": (now + timezone.timedelta(hours=0)).isoformat(),
                "end": (now + timezone.timedelta(hours=1)).isoformat(),
            },
            {
                "start": (now + timezone.timedelta(hours=2)).isoformat(),
                "end": (now + timezone.timedelta(hours=3)).isoformat(),
            },
            {
                "start": (now + timezone.timedelta(hours=4)).isoformat(),
                "end": (now + timezone.timedelta(hours=5)).isoformat(),
            },
        ]
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(DoctorSlot.objects.count(), 3)
        # Verify each slot is for the correct doctor
        for slot in DoctorSlot.objects.all():
            self.assertEqual(slot.doctor.id, self.doctor.id)

    def test_bulk_create_rejects_non_list(self):
        """POST with a single object (not list) returns 400."""
        self.client.force_authenticate(user=self.admin_user)
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        data = {"start": start.isoformat(), "end": end.isoformat()}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Expected a list", str(response.data))
        self.assertEqual(DoctorSlot.objects.count(), 0)

    def test_bulk_create_validation_error_invalid_time_range(self):
        """POST with start >= end fails validation."""
        self.client.force_authenticate(user=self.admin_user)
        start = timezone.now()
        end = start - timezone.timedelta(hours=1)  # end before start
        data = [
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
            }
        ]
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start must be before end", str(response.data))
        self.assertEqual(DoctorSlot.objects.count(), 0)

    def test_bulk_create_partial_failure_stops_on_error(self):
        """POST with invalid slot in list fails entire request."""
        self.client.force_authenticate(user=self.admin_user)
        now = timezone.now()
        data = [
            {
                "start": (now + timezone.timedelta(hours=0)).isoformat(),
                "end": (now + timezone.timedelta(hours=1)).isoformat(),
            },
            {
                "start": (now + timezone.timedelta(hours=2)).isoformat(),
                "end": (now + timezone.timedelta(hours=1)).isoformat(),  # Invalid
            },
        ]
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(DoctorSlot.objects.count(), 0)

    def test_bulk_create_missing_required_fields(self):
        """POST with missing 'start' or 'end' fails validation."""
        self.client.force_authenticate(user=self.admin_user)
        data = [
            {
                "start": timezone.now().isoformat(),
                # missing 'end'
            }
        ]
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end", str(response.data).lower())
        self.assertEqual(DoctorSlot.objects.count(), 0)

    def test_bulk_create_unauthenticated_denied(self):
        """POST without authentication returns 401."""
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        data = [{"start": start.isoformat(), "end": end.isoformat()}]
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(DoctorSlot.objects.count(), 0)

    def test_bulk_create_non_admin_denied(self):
        """POST by non-admin user returns 403."""
        self.client.force_authenticate(user=self.doctor_user)
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        data = [{"start": start.isoformat(), "end": end.isoformat()}]
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(DoctorSlot.objects.count(), 0)

    def test_bulk_create_response_includes_ids_and_timestamps(self):
        """POST response includes id, doctor, start, end, created_at."""
        self.client.force_authenticate(user=self.admin_user)
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        data = [{"start": start.isoformat(), "end": end.isoformat()}]
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        slot_data = response.data[0]
        self.assertIn("id", slot_data)
        self.assertIn("doctor", slot_data)
        self.assertIn("start", slot_data)
        self.assertIn("end", slot_data)
        self.assertIn("created_at", slot_data)
        self.assertEqual(slot_data["doctor"], self.doctor.id)
