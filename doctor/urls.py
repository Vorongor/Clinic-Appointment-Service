from django.urls import path, include
from rest_framework_nested import routers
from .views import DoctorViewSet, DoctorSlotNestedViewSet, DoctorSlotViewSet

router = routers.DefaultRouter()
router.register(r"", DoctorViewSet, basename="doctor")
router.register("slots", DoctorSlotViewSet, basename="slot")

doctor_router = routers.NestedDefaultRouter(
    router,
    "",
    lookup="doctor"
)
doctor_router.register(
    "slots",
    DoctorSlotNestedViewSet,
    basename="doctor-slots"
)

urlpatterns = [
    path("", include(router.urls)),
    path("", include(doctor_router.urls)),
]
