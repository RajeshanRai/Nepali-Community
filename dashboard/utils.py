"""
Utility functions for the dashboard application.

This module contains reusable helper functions for:
- Activity datetime normalization
- Sidebar context data (pending counts)
- Date calculations for analytics
"""

from datetime import datetime, date, time, timedelta
from django.utils import timezone
from django.db.models import Count, Q

# Try to import dateutil for better date calculations
try:
    from dateutil.relativedelta import relativedelta
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


def normalize_activity_datetime(value):
    """
    Normalize a datetime value to a timezone-aware datetime.
    
    Handles mixed date/datetime values consistently for activity timelines.
    
    Args:
        value: A datetime, date, or other value to normalize
        
    Returns:
        A timezone-aware datetime object
    """
    if value is None:
        return timezone.now()
    
    if isinstance(value, datetime):
        dt_value = value
    elif isinstance(value, date):
        dt_value = datetime.combine(value, time.min)
    else:
        dt_value = timezone.now()

    if timezone.is_naive(dt_value):
        dt_value = timezone.make_aware(dt_value, timezone.get_current_timezone())

    return dt_value


def get_sidebar_counts():
    """
    Get sidebar counts for pending projects and applications.
    
    This function aggregates common counts used across multiple views,
    reducing database queries when used as a context processor or helper.
    
    Returns:
        dict: Contains pending_projects_count, pending_applications_count, 
              and unread_notifications_count
    """
    from programs.models import RequestEvent
    from volunteers.models import VolunteerApplication, VolunteerRequest
    
    # Use a single aggregated query to get all counts efficiently
    pending_counts = RequestEvent.objects.aggregate(
        pending_projects=Count('id', filter=Q(status='pending'))
    )
    
    application_counts = VolunteerApplication.objects.aggregate(
        pending_applications=Count('id', filter=Q(status='pending'))
    )
    
    volunteer_request_counts = VolunteerRequest.objects.aggregate(
        pending_requests=Count('id', filter=Q(status='new'))
    )
    
    return {
        'pending_projects_count': pending_counts['pending_projects'],
        'pending_applications_count': (
            application_counts['pending_applications'] + 
            volunteer_request_counts['pending_requests']
        ),
        'unread_notifications_count': 0,  # Placeholder for future notification system
    }


def get_month_date_range(months_ago=0, reference_date=None):
    """
    Get the start and end dates for a month.
    
    Uses relativedelta for accurate month boundaries when possible,
    falling back to 30-day approximation if dateutil is not available.
    
    Args:
        months_ago: Number of months in the past (0 = current month)
        reference_date: Reference date (defaults to now)
        
    Returns:
        tuple: (month_start, month_end) as date objects
    """
    if reference_date is None:
        reference_date = timezone.now()
    
    if HAS_DATEUTIL:
        # Use relativedelta for accurate month calculation
        month_start = (reference_date + relativedelta(months=-months_ago)).replace(day=1)
        month_end = (month_start + relativedelta(months=+1)).replace(day=1) - timedelta(days=1)
    else:
        # Fallback: approximate using 30 days
        approx_date = reference_date - timedelta(days=30 * months_ago)
        month_start = approx_date.replace(day=1)
        # Calculate end of month approximately
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    return month_start, month_end


def get_months_ago(months_ago, reference_date=None):
    """
    Get a date N months ago using accurate month calculations.
    
    Args:
        months_ago: Number of months in the past
        reference_date: Reference date (defaults to now)
        
    Returns:
        datetime: Date N months ago
    """
    if reference_date is None:
        reference_date = timezone.now()
    
    if HAS_DATEUTIL:
        return reference_date + relativedelta(months=-months_ago)
    else:
        # Fallback: approximate using 30 days
        return reference_date - timedelta(days=30 * months_ago)


def format_datetime_for_json(dt_value):
    """
    Format a datetime for JSON serialization.
    
    Args:
        dt_value: A datetime or date value
        
    Returns:
        str: ISO format string or empty string if None
    """
    if dt_value is None:
        return ''
    
    normalized = normalize_activity_datetime(dt_value)
    return normalized.isoformat()


def is_ajax_request(request):
    """
    Check if the request is an AJAX request.
    
    Checks the X-Requested-With header which is set by
    jQuery and other JavaScript frameworks.
    
    Args:
        request: HTTP request object
        
    Returns:
        bool: True if the request is AJAX
    """
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def json_response(data, status=200):
    """
    Create a JSON response.
    
    Args:
        data: Dictionary to serialize as JSON
        status: HTTP status code
        
    Returns:
        JsonResponse: Django JSON response object
    """
    from django.http import JsonResponse
    return JsonResponse(data, status=status)


def success_json_response(message, extra_data=None):
    """
    Create a success JSON response.
    
    Args:
        message: Success message
        extra_data: Optional extra data to include
        
    Returns:
        JsonResponse: Django JSON response with success status
    """
    data = {
        'success': True,
        'message': message,
    }
    if extra_data:
        data.update(extra_data)
    return json_response(data)


def error_json_response(message, status=400, extra_data=None):
    """
    Create an error JSON response.
    
    Args:
        message: Error message
        status: HTTP status code (default 400 for bad request)
        extra_data: Optional extra data to include
        
    Returns:
        JsonResponse: Django JSON response with error status
    """
    data = {
        'success': False,
        'message': message,
    }
    if extra_data:
        data.update(extra_data)
    return json_response(data, status=status)


def get_annotated_communities():
    """
    Get communities with annotated counts for programs.
    
    Uses annotate to efficiently get program counts per community
    in a single query instead of N+1 queries.
    
    Returns:
        QuerySet: Communities with num_programs annotation
    """
    from communities.models import Community
    return Community.objects.annotate(num_programs=Count('programs'))


def get_annotated_events_for_analytics():
    """
    Get events with annotated counts for registrations.
    
    Uses annotate to efficiently get registration counts
    in a single query.
    
    Returns:
        QuerySet: Programs with registration_count annotation
    """
    from programs.models import Program
    return Program.objects.annotate(registration_count=Count('registrations'))
