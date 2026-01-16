from django.test import TestCase
from doctor.models import Doctor
from doctor.serializers import DoctorSerializer
from specializations.models import Specialization


class DoctorSerializerTests(TestCase):
    def setUp(self):
        self.specialization = Specialization.objects.create(name="Cardiology")
        self.doctor = Doctor.objects.create(
            first_name="John",
            last_name="Doe",
            price_per_visit="50.00",
        )
        self.doctor.specializations.add(self.specialization)

    def test_serialize_doctor(self):
        serializer = DoctorSerializer(self.doctor)
        data = serializer.data
        self.assertEqual(data["first_name"], "John")
        self.assertEqual(data["last_name"], "Doe")
        self.assertEqual(data["price_per_visit"], "50.00")
        self.assertIn(self.specialization.id, data["specializations"])

    def test_deserialize_valid_data(self):
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "price_per_visit": "75.00",
            "specializations": [self.specialization.id]
        }
        serializer = DoctorSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        doctor = serializer.save()
        self.assertEqual(doctor.first_name, "Jane")
        self.assertEqual(doctor.last_name, "Smith")
        self.assertEqual(str(doctor.price_per_visit), "75.00")
        self.assertIn(self.specialization, doctor.specializations.all())

    def test_deserialize_invalid_data_missing_first_name(self):
        data = {
            "last_name": "Smith",
            "price_per_visit": "75.00",
            "specializations": [self.specialization.id]
        }
        serializer = DoctorSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("first_name", serializer.errors)
