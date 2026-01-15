from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError

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
