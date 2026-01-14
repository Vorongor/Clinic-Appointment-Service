from django.test import TestCase

from specializations.models import Specialization
from specializations.serializers import SpecializationSerializer


class SpecializationSerializerTests(TestCase):
    def test_serializer_fields_and_data(self):
        spec = Specialization.objects.create(
            name="Cardiology",
            code="cardio",
            description="Heart",
        )
        ser = SpecializationSerializer(spec)
        self.assertEqual(set(ser.data.keys()), {"id", "name", "code", "description"})
        self.assertEqual(ser.data["name"], "Cardiology")

    def test_serializer_create(self):
        data = {"name": "Dermatology", "code": "derm", "description": "Skin"}
        ser = SpecializationSerializer(data=data)
        self.assertTrue(ser.is_valid(), ser.errors)
        spec = ser.save()
        self.assertEqual(spec.name, "Dermatology")
