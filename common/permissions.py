from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


class SuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_active and request.user.is_superuser)


class CatalogAccess(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        profile = getattr(user, 'profile', None)
        return bool(profile and profile.tenant and profile.tenant.status == 'ACTIVE' and profile.role and profile.role.can_manage_catalog)


def confirm_password(request):
    password = request.data.get('admin_password', '') if hasattr(request.data, 'get') else ''
    if not isinstance(password, str) or not request.user.check_password(password):
        raise PermissionDenied('Your current admin_password is required.')
