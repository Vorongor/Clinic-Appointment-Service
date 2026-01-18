from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter
from user.permissions import IsAdminOrReadOnly
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Specialization
from .serializers import SpecializationSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List specializations",
        description="Retrieve a list of all medical specializations. "
                    "Supports search by name, code, and description.",
        parameters=[
            {
                "name": "search",
                "in": "query",
                "description": "Search specializations by name, "
                               "code, or description",
                "required": False,
                "schema": {"type": "string"}
            }
        ]
    ),
    create=extend_schema(
        summary="Create a specialization",
        description="Create a new medical specialization."
    ),
    retrieve=extend_schema(
        summary="Retrieve a specialization",
        description="Retrieve details of a specific medical specialization."
    ),
    update=extend_schema(
        summary="Update a specialization",
        description="Update an existing medical specialization."
    ),
    partial_update=extend_schema(
        summary="Partially update a specialization",
        description="Partially update an existing medical specialization."
    ),
    destroy=extend_schema(
        summary="Delete a specialization",
        description="Delete a medical specialization."
    ),
)
class SpecializationViewSet(ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [SearchFilter]
    search_fields = ["name", "code", "description"]
