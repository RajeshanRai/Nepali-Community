"""
Centralized decorators and permission helpers for dashboard module.
"""
from functools import wraps
from django.contrib.auth.decorators import user_passes_test as django_user_passes_test
from django.shortcuts import redirect
from django.urls import reverse_lazy


def staff_required(user):
    """
    Check if user has staff or superuser status.
    Used with @user_passes_test(staff_required, login_url='login')
    """
    return user.is_active and (user.is_staff or user.is_superuser)


def superuser_required(user):
    """
    Check if user is a superuser.
    Used with @user_passes_test(superuser_required, login_url='login')
    """
    return user.is_active and user.is_superuser


def admin_required(view_func):
    """
    Decorator for staff/superuser-only views.
    Redirects to login if user is not authenticated as staff/superuser.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapped_view
