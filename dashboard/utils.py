"""
Utility functions for the dashboard application.

This module contains reusable helper functions for:
- Activity datetime normalization
- Sidebar context data (pending counts)
- Date calculations for analytics
"""

from datetime import datetime, date, time, timedelta
from django.urls import reverse
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


def get_dashboard_notifications(user=None, limit=18, dropdown_limit=6):
    """
    Build the live dashboard notifications feed.

    Returns a shared notification payload so the navbar dropdown and
    notifications page render the same items and counts.
    """
    from announcements.models import Announcement
    from contacts.models import ContactMessage
    from programs.models import RequestEvent
    from volunteers.models import VolunteerApplication, VolunteerRequest
    from dashboard.models import AdminNotificationState

    now = timezone.now()
    notifications_feed = []
    last_read_at = None

    if user and getattr(user, 'is_authenticated', False):
        notification_state = AdminNotificationState.objects.filter(user=user).only('last_read_at').first()
        if notification_state and notification_state.last_read_at:
            last_read_at = notification_state.last_read_at

    pending_projects = list(
        RequestEvent.objects.filter(status='pending')
        .select_related('community')
        .order_by('-submitted_at')[:6]
    )
    pending_volunteer_applications = list(
        VolunteerApplication.objects.filter(status='pending')
        .select_related('opportunity')
        .order_by('-applied_at')[:6]
    )
    pending_volunteer_requests = list(
        VolunteerRequest.objects.filter(status='new')
        .order_by('-created_at')[:6]
    )
    recent_contacts = list(ContactMessage.objects.order_by('-created_at')[:6])
    recent_announcements = list(Announcement.objects.order_by('-created_at')[:4])

    def push_notification(message, created_at, url, icon, bg_class, default_unread=True):
        normalized_created_at = normalize_activity_datetime(created_at)
        unread = default_unread if last_read_at is None else normalized_created_at > last_read_at
        notifications_feed.append({
            'message': message,
            'created_at': normalized_created_at,
            'url': url,
            'icon': icon,
            'bg_class': bg_class,
            'unread': unread,
        })

    for req in pending_projects:
        push_notification(
            f'Project request pending review: {req.title}',
            req.submitted_at,
            reverse('dashboard:event_requests_list'),
            'fas fa-clock',
            'bg-warning',
        )

    for app in pending_volunteer_applications:
        push_notification(
            f'Volunteer application from {app.name} for {app.opportunity.title}',
            app.applied_at,
            reverse('dashboard:volunteers_applications'),
            'fas fa-user-check',
            'bg-success',
        )

    for volunteer_request in pending_volunteer_requests:
        push_notification(
            f'New volunteer request from {volunteer_request.name}',
            volunteer_request.created_at,
            reverse('dashboard:volunteers_applications'),
            'fas fa-hands-helping',
            'bg-info',
        )

    for contact in recent_contacts:
        push_notification(
            f'Contact message received: {contact.subject}',
            contact.created_at,
            reverse('dashboard:contact_messages_list'),
            'fas fa-envelope-open-text',
            'bg-danger',
            default_unread=contact.created_at >= now - timedelta(days=7),
        )

    for announcement in recent_announcements:
        push_notification(
            f'Announcement published: {announcement.title}',
            announcement.created_at,
            reverse('dashboard:announcements_list'),
            'fas fa-bullhorn',
            'bg-primary',
            default_unread=announcement.created_at >= now - timedelta(days=3),
        )

    notifications_feed = sorted(
        notifications_feed,
        key=lambda item: item['created_at'],
        reverse=True,
    )[:limit]
    dropdown_notifications = notifications_feed[:dropdown_limit]

    pending_projects_count = RequestEvent.objects.filter(status='pending').count()
    pending_volunteer_applications_count = VolunteerApplication.objects.filter(status='pending').count()
    pending_volunteer_requests_count = VolunteerRequest.objects.filter(status='new').count()
    recent_contact_count = ContactMessage.objects.filter(
        created_at__gte=now - timedelta(days=7)
    ).count()

    return {
        'pending_projects_count': pending_projects_count,
        'pending_applications_count': (
            pending_volunteer_applications_count + pending_volunteer_requests_count
        ),
        'unread_notifications_count': sum(1 for item in notifications_feed if item['unread']),
        'notifications_feed': notifications_feed,
        'dropdown_notifications': dropdown_notifications,
        'notification_totals': {
            'project_requests': pending_projects_count,
            'volunteer_applications': pending_volunteer_applications_count,
            'volunteer_requests': pending_volunteer_requests_count,
            'contact_messages': recent_contact_count,
        },
    }


def get_sidebar_counts(user=None):
    """
    Get sidebar counts for pending projects and applications.
    
    This function aggregates common counts used across multiple views,
    reducing database queries when used as a context processor or helper.
    
    Returns:
        dict: Contains pending_projects_count, pending_applications_count, 
              and unread_notifications_count
    """
    notification_data = get_dashboard_notifications(user=user, limit=6, dropdown_limit=6)
    return {
        'pending_projects_count': notification_data['pending_projects_count'],
        'pending_applications_count': notification_data['pending_applications_count'],
        'unread_notifications_count': notification_data['unread_notifications_count'],
        'dropdown_notifications': notification_data['dropdown_notifications'],
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
