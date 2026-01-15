from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from user.permissions import IsAdminOrReadOnly

from .models import Doctor, DoctorSlot
from .serializers import DoctorSerializer, DoctorSlotSerializer
from appointment.models import Appointment


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["specializations"]
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=True, methods=["get", "post"], url_path="slots")
    def slots(self, request, pk=None):
        doctor = self.get_object()
        if request.method == "POST":
            data = request.data
            if not isinstance(data, list):
                return Response(
                    {"detail": "Expected a list of slots"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = DoctorSlotSerializer(data=data, many=True)
            serializer.is_valid(raise_exception=True)
            created = []

            for item in serializer.validated_data:
                slot = DoctorSlot.objects.create(
                    doctor=doctor,
                    start=item["start"],
                    end=item["end"]
                )
                created.append(slot)

            out_serializer = DoctorSlotSerializer(created, many=True)
            return Response(
                out_serializer.data,
                status=status.HTTP_201_CREATED
            )

        qs = doctor.slots.all()

        from_param = request.query_params.get("from")
        to_param = request.query_params.get("to")
        if from_param:
            qs = qs.filter(start__gte=from_param)
        if to_param:
            qs = qs.filter(end__lte=to_param)

        available_only = request.query_params.get("available_only")
        if available_only in ["true", "True", "1"]:
            qs = qs.annotate(
                booked_count=Count(
                    "appointments",
                    filter=Q(
                        appointments__status=Appointment.Status.BOOKED
                    )
                )
                ).filter(booked_count=0)

        serializer = DoctorSlotSerializer(qs, many=True)
        return Response(serializer.data)


class DoctorSlotViewSet(
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """Provides retrieve and destroy for individual slots."""
    queryset = DoctorSlot.objects.all()
    serializer_class = DoctorSlotSerializer
    permission_classes = [IsAdminOrReadOnly]

    def destroy(self, request, pk=None):
        slot = self.get_object()

        if slot.appointments.exists():
            return Response(
                {"detail": "Cannot delete slot with existing appointments"},
                status=status.HTTP_400_BAD_REQUEST
            )

        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
