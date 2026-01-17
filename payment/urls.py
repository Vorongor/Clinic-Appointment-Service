from django.urls import path, include

from rest_framework.routers import DefaultRouter

from payment.views import PaymentViewSet, StripeWebhookView

router = DefaultRouter()
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("", include(router.urls)),
]
