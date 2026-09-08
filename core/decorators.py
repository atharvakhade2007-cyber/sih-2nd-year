from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.contrib import messages


def role_required(*allowed_roles):
    """Decorator enforcing role-based access on views."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("core:login")
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                messages.error(request, "You are not authorized to access this page.")
                return HttpResponseForbidden("Access Denied: Insufficient Role Permissions")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
