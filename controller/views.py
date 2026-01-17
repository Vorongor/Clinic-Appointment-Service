from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
def initial_develop_endpoint(request: Request) -> Response:
    return Response(
        status=status.HTTP_200_OK,
        data={
            "message": "Connection established!",
        },
    )
