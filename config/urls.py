from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularSwaggerView,
    SpectacularAPIView,
    SpectacularRedocView,
)
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter
from doctor.views import DoctorSlotViewSet


slot_router = DefaultRouter()
slot_router.register("", DoctorSlotViewSet, basename="slot")


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(
            permission_classes=[AllowAny], url_name="schema"
        ),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(
            permission_classes=[AllowAny],
            url_name="schema"
        ),
        name="redoc",
    ),
    path("api/user/", include("user.urls", namespace="user")),
    path("api/", include("doctor.urls")),
    path("api/appointments/", include("appointment.urls")),
    path("api/specializations/", include("specializations.urls")),
    path("api/payments/", include("payment.urls")),
]
