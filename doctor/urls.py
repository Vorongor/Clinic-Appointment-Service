from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorViewSet

router = DefaultRouter()
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("slots", DoctorViewSet, basename="slot")

urlpatterns = [
    path("", include(router.urls)),
]
