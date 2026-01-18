import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from appointment.models import Appointment
from doctor.models import DoctorSlot, Doctor
from specializations.models import Specialization


class BaseTestCaseModel(TestCase):

    def setUp(self):
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
        self.doctor.save()
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