from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    DoctorViewSet,
    DoctorSlotNestedViewSet,
    DoctorSlotViewSet
)

<<<<<<< HEAD
router = routers.DefaultRouter()
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("slots", DoctorSlotViewSet, basename="slot")

doctor_router = routers.NestedDefaultRouter(router, "doctors", lookup="doctor")
doctor_router.register(
    "slots",
    DoctorSlotNestedViewSet,
    basename="doctor-slots"
)
=======
router = DefaultRouter()
router.register("", DoctorViewSet, basename="doctor")
router.register("slots", DoctorViewSet, basename="slot")
>>>>>>> origin/develop

urlpatterns = [
    path("", include(router.urls)),
    path("", include(doctor_router.urls)),
]
