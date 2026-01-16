from drf_spectacular.views import SpectacularSwaggerView, SpectacularRedocView, \
    SpectacularAPIView
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


@api_view(["GET"])
def initial_develop_endpoint(request: Request) -> Response:
    return Response(
        status=status.HTTP_200_OK,
        data={
            "message": "Connection established!",
        },
    )


class SpectacularAPIViewUP(SpectacularAPIView):
    permission_classes = ()
    authentication_classes = ()

class SpectacularSwaggerViewUP(SpectacularSwaggerView):
    permission_classes = ()
    authentication_classes = ()


class SpectacularRedocViewUP(SpectacularRedocView):
    permission_classes = ()
    authentication_classes = ()