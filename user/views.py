from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema, extend_schema_view

from user.models import Patient
from user.serializers import UserSerializer, PatientSerializer
from user.mixins import UserLogicMixin


TokenObtainPairView = extend_schema_view(
    post=extend_schema(tags=["User"])
)(TokenObtainPairView)


TokenRefreshView = extend_schema_view(
    post=extend_schema(tags=["User"])
)(TokenRefreshView)


@extend_schema(tags=["User"])
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema(tags=["User"])
class ManageUserView(UserLogicMixin, generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        self.perform_user_update(serializer)


@extend_schema(tags=["Patient"])
class PatientViewSet(UserLogicMixin, viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        self.perform_patient_create(serializer)
