from rest_framework.routers import DefaultRouter
from .views import SpecializationViewSet

router = DefaultRouter()
router.register(
    "specializations",
    SpecializationViewSet,
    basename="specialization"
)

urlpatterns = router.urls
