from rest_framework.permissions import BasePermission

from .models import User


class IsAdmin(BasePermission):
    """Only users with the Admin role."""

    message = "Admin access required."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsAnalystOrAbove(BasePermission):
    """Analyst or Admin."""

    message = "Analyst or Admin access required."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in {User.Role.ANALYST, User.Role.ADMIN}
        )


class IsActiveUser(BasePermission):
    """Reject inactive users even if authenticated."""

    message = "Your account has been deactivated."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_active


class RecordPermission(BasePermission):
    """
    Role-aware permission for financial records:
      - Viewer  → GET only (list + detail)
      - Analyst → GET only
      - Admin   → full CRUD
    """

    message = "You do not have permission to perform this action."

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in self.SAFE_METHODS:
            # All roles can read
            return True

        # Write operations restricted to Admin
        return request.user.role == User.Role.ADMIN