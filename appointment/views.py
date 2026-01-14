from django.shortcuts import render
from rest_framework import viewsets

from appointment.models import Appointment
from appointment.serializers import AppointmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
