from rest_framework import serializers

from .models import Doctor
from specializations.models import Specialization


class DoctorSerializer(serializers.ModelSerializer):
    specializations = serializers.PrimaryKeyRelatedField(
        queryset=Specialization.objects.all(),
        many=True
    )

    class Meta:
        model = Doctor
        fields = "__all__"
