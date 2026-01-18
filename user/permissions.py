from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS
            or (request.user and request.user.is_staff)
        )


class IsOwnerOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return bool(
            (request.user and request.user.is_staff)
            or (obj.user == request.user)
        )
