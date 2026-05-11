"""
Context processors for the dashboard application.

These processors add common sidebar data to all template contexts,
eliminating the need to manually add these counts in every view.
"""

from .utils import get_sidebar_counts


def sidebar_counts(request):
    """
    Add sidebar counts to the context for all authenticated admin users.
    
    This context processor is called for every template render when
    the user is authenticated and is a superuser.
    
    To enable, add this to TEMPLATES settings:
    
        'OPTIONS': {
            'context_processors': [
                ...
                'dashboard.context_processors.sidebar_counts',
            ],
        }
    
    Returns:
        dict: Sidebar counts or empty dict for non-admin users
    """
    # Only add counts for authenticated admin users
    if not request.user.is_authenticated:
        return {}
    
    if not request.user.is_superuser:
        return {}
    
    # Use the optimized utility function
    return get_sidebar_counts(request.user)


def admin_info(request):
    """
    Add admin-specific information to the context.
    
    Returns:
        dict: Admin-related flags and information
    """
    if not request.user.is_authenticated:
        return {}
    
    return {
        'is_admin': request.user.is_superuser,
    }
