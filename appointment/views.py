from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters

from appointment.filters import AppointmentFilter
from appointment.models import Appointment
from appointment.serializers import (
    AppointmentSerializer,
    AppointmentListSerializer,
    AppointmentDetailSerializer,
)


class AppointmentViewSet(viewsets.ModelViewSet):

    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    action_serializers = {
        "retrieve": AppointmentDetailSerializer,
        "list": AppointmentListSerializer,
    }

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "doctor__first_name",
        "doctor__last_name",
    ]
    filterset_class = AppointmentFilter

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Appointment.objects.all()
        return Appointment.objects.filter(patient_id=user.id)
