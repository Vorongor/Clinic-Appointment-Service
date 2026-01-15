from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from payment.models import Payment
from payment.serializers import PaymentSerializer


@extend_schema(tags=["Payments"])
class PaymentViewSet(ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related("appointment", "appointment__patient")

        if user.is_staff:
            return qs
        return qs.filter(appointment__patient=user)
