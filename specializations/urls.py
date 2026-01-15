from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SpecializationViewSet

router = DefaultRouter()
router.register(
    "",
    SpecializationViewSet,
    basename="specialization"
)

urlpatterns = [
    path("", include(router.urls))
]
