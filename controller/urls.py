from django.urls import path

from controller.views import initial_develop_endpoint

urlpatterns = [
    path("", initial_develop_endpoint, name="index"),
]

app_name = "controller"