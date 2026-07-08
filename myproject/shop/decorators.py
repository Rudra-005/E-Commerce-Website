from django.shortcuts import redirect


def jwt_login_required(view_func):

    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("login")

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


from django.http import HttpResponseForbidden
from functools import wraps
from .auth_helpers import verify_token

def require_role(allowed_roles):
    """
    Decorator to require specific roles for accessing a view.
    allowed_roles can be a string or a list of strings.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            
            if user and user.is_authenticated:
                if user.is_superuser or (hasattr(user, 'userprofile') and user.userprofile.role in allowed_roles):
                    return view_func(request, *args, **kwargs)

            access_token = request.COOKIES.get("access_token")
            if access_token:
                payload = verify_token(access_token, "access")
                if payload:
                    from django.contrib.auth.models import User
                    try:
                        resolved_user = User.objects.get(id=payload.get("user_id"))
                        if resolved_user.is_superuser or payload.get("role") in allowed_roles:
                            request.user = resolved_user
                            return view_func(request, *args, **kwargs)
                    except User.DoesNotExist:
                        pass
                    
                    return HttpResponseForbidden("You do not have permission to access this page.")

            # If no valid token and not authenticated, redirect to login
            return redirect("login")
        return _wrapped_view
    return decorator

def require_permission(permission_name):
    """
    Decorator to require a specific permission for accessing a view.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            
            if user and user.is_authenticated:
                if user.is_superuser or (hasattr(user, 'userprofile') and permission_name in user.userprofile.permissions):
                    return view_func(request, *args, **kwargs)

            access_token = request.COOKIES.get("access_token")
            if access_token:
                payload = verify_token(access_token, "access")
                if payload:
                    from django.contrib.auth.models import User
                    try:
                        resolved_user = User.objects.get(id=payload.get("user_id"))
                        if resolved_user.is_superuser or permission_name in payload.get("permissions", []):
                            request.user = resolved_user
                            return view_func(request, *args, **kwargs)
                    except User.DoesNotExist:
                        pass

            return HttpResponseForbidden(f"You require the '{permission_name}' permission to access this page.")
        return _wrapped_view
    return decorator