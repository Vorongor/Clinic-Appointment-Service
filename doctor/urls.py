from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    DoctorViewSet,
    DoctorSlotNestedViewSet,
    DoctorSlotViewSet
)

router = routers.DefaultRouter()
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("slots", DoctorSlotViewSet, basename="slot")

doctor_router = routers.NestedDefaultRouter(router, "doctors", lookup="doctor")
doctor_router.register(
    "slots",
    DoctorSlotNestedViewSet,
    basename="doctor-slots"
)

urlpatterns = [
    path("", include(router.urls)),
    path("", include(doctor_router.urls)),
]
