"""
Admin Dashboard API endpoints for analytics data
Provides JSON responses for dashboard charts and statistics
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
import json

from users.models import CustomUser
from programs.models import Program, EventRegistration, RequestEvent
from donations.models import Donation
from communities.models import Community
from contacts.models import ContactMessage


def staff_required(user):
    """Check if user is an active superuser"""
    return user.is_active and user.is_superuser


@require_http_methods(["GET"])
@user_passes_test(staff_required, login_url='login')
def get_user_analytics(request):
    """API endpoint for user analytics data"""
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    try:
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(last_login__gte=thirty_days_ago).count()
        new_users_this_month = CustomUser.objects.filter(date_joined__gte=now.replace(day=1)).count()
        verified_users = CustomUser.objects.filter(is_verified_member=True).count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'total_users': total_users,
                'active_users': active_users,
                'new_users_this_month': new_users_this_month,
                'verified_users': verified_users,
                'unverified_users': total_users - verified_users,
                'active_percentage': round((active_users / total_users * 100) if total_users > 0 else 0, 1),
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@user_passes_test(staff_required, login_url='login')
def get_event_analytics(request):
    """API endpoint for event analytics data"""
    today = timezone.now().date()
    
    try:
        total_events = Program.objects.count()
        upcoming_events = Program.objects.filter(date__gte=today).count()
        completed_events = Program.objects.filter(date__lt=today).count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'total_events': total_events,
                'upcoming_events': upcoming_events,
                'completed_events': completed_events,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@user_passes_test(staff_required, login_url='login')
def get_chart_data(request):
    """API endpoint for all chart data"""
    try:
        now = timezone.now()
        
        # Monthly user growth
        months_data = {}
        for i in range(11, -1, -1):
            date = now - timedelta(days=30*i)
            month_key = date.strftime('%b %Y')
            month_start = date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            count = CustomUser.objects.filter(
                date_joined__gte=month_start,
                date_joined__lt=month_end
            ).count()
            
            months_data[month_key] = count
        
        # Active vs inactive users
        thirty_days_ago = now - timedelta(days=30)
        active = CustomUser.objects.filter(last_login__gte=thirty_days_ago).count()
        inactive = CustomUser.objects.filter(
            Q(last_login__lt=thirty_days_ago) | Q(last_login__isnull=True)
        ).count()
        
        # Event status distribution
        today = now.date()
        upcoming = Program.objects.filter(date__gte=today).count()
        completed = Program.objects.filter(date__lt=today).count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'monthly_user_growth': {
                    'labels': list(months_data.keys()),
                    'data': list(months_data.values()),
                },
                'user_status': {
                    'labels': ['Active (30d)', 'Inactive'],
                    'data': [active, inactive],
                },
                'event_status': {
                    'labels': ['Upcoming', 'Completed'],
                    'data': [upcoming, completed],
                }
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@user_passes_test(staff_required, login_url='login')
def get_system_health(request):
    """API endpoint for overall system health metrics"""
    try:
        now = timezone.now()
        # Quick metrics
        total_users = CustomUser.objects.count()
        total_events = Program.objects.count()
        total_registrations = EventRegistration.objects.count()
        pending_requests = RequestEvent.objects.filter(status='pending').count()
        unread_messages = ContactMessage.objects.count()  # Adjust if you have a read_at field
        
        # Calculate engagement rate
        engaged_users = CustomUser.objects.filter(
            eventregistration__isnull=False
        ).distinct().count()
        engagement_rate = (engaged_users / total_users * 100) if total_users > 0 else 0
        
        return JsonResponse({
            'success': True,
            'data': {
                'users': total_users,
                'events': total_events,
                'registrations': total_registrations,
                'pending_requests': pending_requests,
                'messages': unread_messages,
                'engagement_rate': round(engagement_rate, 1),
                'timestamp': now.isoformat(),
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@user_passes_test(staff_required, login_url='login')
def export_analytics(request):
    """Export analytics data as JSON"""
    try:
        # Collect comprehensive data
        analytics_data = {
            'export_date': timezone.now().isoformat(),
            'users': {
                'total': CustomUser.objects.count(),
                'active_30d': CustomUser.objects.filter(
                    last_login__gte=timezone.now() - timedelta(days=30)
                ).count(),
                'verified': CustomUser.objects.filter(is_verified_member=True).count(),
            },
            'events': {
                'total': Program.objects.count(),
                'by_type': list(Program.objects.values('event_type').annotate(count=Count('id'))),
            },
            'registrations': {
                'total': EventRegistration.objects.count(),
                'unique_users': EventRegistration.objects.values('user').distinct().count(),
            },
            'requests': {
                'pending': RequestEvent.objects.filter(status='pending').count(),
                'handled': RequestEvent.objects.exclude(status='pending').count(),
            },
            'donations': {
                'total_amount': float(Donation.objects.aggregate(Sum('amount'))['amount__sum'] or 0),
                'count': Donation.objects.count(),
            }
        }
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@user_passes_test(staff_required, login_url='login')
def get_available_opportunities(request):
    """Get list of available volunteer opportunities for assignment"""
    from volunteers.models import VolunteerOpportunity
    try:
        opportunities = VolunteerOpportunity.objects.filter(
            status='open'
        ).values('id', 'title', 'category', 'start_date', 'end_date', 'positions_remaining').order_by('-created_at')
        
        return JsonResponse({
            'success': True,
            'opportunities': list(opportunities)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
