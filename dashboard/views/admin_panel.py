"""
Admin Panel and Analytics Views
Contains the main dashboard view and advanced admin panel functionality.
"""

from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum, Q, Avg, Case, When, IntegerField
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.contrib import messages
from datetime import timedelta, datetime, date, time
import json

from users.models import CustomUser
from programs.models import Program, EventRegistration, RequestEvent
from donations.models import Donation
from communities.models import Community
from contacts.models import ContactMessage
from volunteers.models import VolunteerApplication, VolunteerOpportunity, VolunteerRequest
from announcements.models import Announcement
from faqs.models import FAQ, FAQCategory


def staff_required(user):
    """Check if user is staff or superuser"""
    return user.is_active and (user.is_staff or user.is_superuser)


def admin_required(view_func):
    """Decorator to require staff or superuser status"""
    def wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapped_view


@method_decorator(user_passes_test(staff_required, login_url='login'), name='dispatch')
@method_decorator(cache_page(300), name='dispatch')  # Cache for 5 minutes
class DashboardView(TemplateView):
    template_name = 'dashboard/legacy/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # ===== USER ANALYTICS SECTION =====
        context.update(self.get_user_analytics())
        
        # ===== EVENT ANALYTICS SECTION =====
        context.update(self.get_event_analytics())
        
        # ===== ATTENDANCE & PARTICIPATION SECTION =====
        context.update(self.get_attendance_analytics())
        
        # ===== REQUESTS & SYSTEM ACTIVITY SECTION =====
        context.update(self.get_request_activity_analytics())
        
        # ===== ENGAGEMENT INSIGHTS SECTION =====
        context.update(self.get_engagement_analytics())
        
        # ===== DONATION ANALYTICS =====
        context.update(self.get_donation_analytics())
        
        # Chart data
        context.update(self.get_chart_data())
        
        # ===== ADDITIONAL CONTEXT VARIABLES =====
        # Total communities
        context['total_communities'] = Community.objects.count()
        
        # Verified members (check correct field name)
        context['verified_members'] = context.get('verified_users', 0)
        
        # Past events
        today = timezone.now().date()
        context['past_events'] = Program.objects.filter(date__lt=today).count()
        
        # Pending requests
        context['pending_requests'] = context.get('pending_event_requests', 0)
        
        # Recent requests (ensure it exists)
        if 'recent_requests' not in context:
            context['recent_requests'] = RequestEvent.objects.all().order_by('-submitted_at')[:10]
        
        # Top events (most registered)
        top_events = Program.objects.annotate(
            registration_count=Count('registrations')
        ).order_by('-registration_count')[:5]
        context['top_events'] = top_events
        
        # Registered percentage (users with at least one registration)
        if context['total_users'] > 0:
            users_with_registrations = CustomUser.objects.filter(
                eventregistration__isnull=False
            ).distinct().count()
            context['registered_percentage'] = round(
                (users_with_registrations / context['total_users']) * 100, 1
            )
        else:
            context['registered_percentage'] = 0
        
        return context
    
    def get_user_analytics(self):
        """Get comprehensive user statistics"""
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # OPTIMIZED: Single aggregation query instead of 5 separate count() calls
        # Reduces from 5-6 queries to 1 query
        user_stats = CustomUser.objects.aggregate(
            total_users=Count('id'),
            active_users=Count('id', filter=Q(last_login__gte=thirty_days_ago)),
            new_users_this_month=Count('id', filter=Q(date_joined__gte=now.replace(day=1))),
            verified_users=Count('id', filter=Q(is_verified_member=True)),
            staff_users=Count('id', filter=Q(is_staff=True)),
        )
        
        total_users = user_stats['total_users']
        active_users = user_stats['active_users']
        verified_users = user_stats['verified_users']
        unverified_users = total_users - verified_users
        
        # Recently joined users
        recently_joined = CustomUser.objects.all().order_by('-date_joined')[:10]
        
        # Active users percentage
        active_percentage = (active_users / total_users * 100) if total_users > 0 else 0
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'active_percentage': round(active_percentage, 1),
            'new_users_this_month': user_stats['new_users_this_month'],
            'verified_users': verified_users,
            'unverified_users': unverified_users,
            'recently_joined': recently_joined,
            'staff_users': user_stats['staff_users'],
        }
    
    def get_event_analytics(self):
        """Get comprehensive event statistics"""
        now = timezone.now()
        today = now.date()
        
        # OPTIMIZED: Single aggregation query instead of 4 separate count() calls
        # Reduces from 4-5 queries to 1 query
        event_stats = Program.objects.aggregate(
            total_events=Count('id'),
            upcoming_events=Count('id', filter=Q(date__gte=today)),
            ongoing_events=Count('id', filter=Q(date=today)),
            completed_events=Count('id', filter=Q(date__lt=today)),
        )
        total_events = event_stats['total_events']
        upcoming_events = event_stats['upcoming_events']
        ongoing_events = event_stats['ongoing_events']
        completed_events = event_stats['completed_events']
        
        # Event types breakdown
        event_types = Program.objects.values('event_type').annotate(count=Count('id')).order_by('-count')
        
        # Most popular events
        most_popular = Program.objects.annotate(
            reg_count=Count('registrations')
        ).order_by('-reg_count')[:5]
        
        # Least engaged events
        least_engaged = Program.objects.annotate(
            reg_count=Count('registrations')
        ).filter(reg_count__gt=0).order_by('reg_count')[:5]
        
        return {
            'total_events': total_events,
            'upcoming_events': upcoming_events,
            'ongoing_events': ongoing_events,
            'completed_events': completed_events,
            'most_popular_events': most_popular,
            'least_engaged_events': least_engaged,
            'event_types': event_types,
        }
    
    def get_attendance_analytics(self):
        """Get attendance and participation statistics"""
        events_with_attendance = Program.objects.annotate(
            attendee_count=Count('registrations', distinct=True)
        ).order_by('-attendee_count')
        
        total_registrations = EventRegistration.objects.count()
        unique_registered_users = EventRegistration.objects.values('user').distinct().count()
        
        # Top 5 highest attended events
        top_attended = events_with_attendance[:5]
        
        # Calculate average attendance
        avg_attendance = events_with_attendance.aggregate(
            avg=Avg('attendee_count')
        )['avg'] or 0
        
        return {
            'total_registrations': total_registrations,
            'unique_registered_users': unique_registered_users,
            'top_attended_events': top_attended,
            'average_attendance': round(avg_attendance, 1),
        }
    
    def get_request_activity_analytics(self):
        """Get pending requests and system activity"""
        pending_event_requests = RequestEvent.objects.filter(status='pending').count()
        total_requests = RequestEvent.objects.count()
        
        # Recent contact messages
        recent_contacts = ContactMessage.objects.all().order_by('-created_at')[:10]
        
        # Recent requests
        recent_requests = RequestEvent.objects.all().order_by('-submitted_at')[:10]
        
        return {
            'pending_event_requests': pending_event_requests,
            'handled_requests': RequestEvent.objects.exclude(status='pending').count(),
            'total_requests': total_requests,
            'recent_contacts': recent_contacts,
            'recent_requests': recent_requests,
        }
    
    def get_engagement_analytics(self):
        """Get engagement metrics and insights"""
        # Most active users (by event registrations)
        most_active_users = CustomUser.objects.annotate(
            event_count=Count('eventregistration')
        ).filter(event_count__gt=0).order_by('-event_count')[:5]
        
        # OPTIMIZED: Single aggregation query instead of 2 separate count() calls
        # Reduces from 2-3 queries to 1 query
        now = timezone.now()
        retention_stats = CustomUser.objects.aggregate(
            users_active_30=Count('id', filter=Q(last_login__gte=now - timedelta(days=30))),
            users_active_60=Count('id', filter=Q(last_login__gte=now - timedelta(days=60))),
        )
        
        users_active_30 = retention_stats['users_active_30']
        users_active_60 = retention_stats['users_active_60']
        retention_rate = (users_active_30 / users_active_60 * 100) if users_active_60 > 0 else 0
        
        return {
            'most_active_users': most_active_users,
            'retention_rate': round(retention_rate, 1),
        }
    
    def get_donation_analytics(self):
        """Get donation statistics"""
        # OPTIMIZED: Single aggregation query instead of 4 separate queries
        # Reduces from 4 separate queries to 1 query
        now = timezone.now()
        donation_stats = Donation.objects.aggregate(
            total_donations=Count('id'),
            total_amount=Sum('amount'),
            recurring_donations=Count('id', filter=Q(is_recurring=True)),
            this_month_amount=Sum('amount', filter=Q(created_at__year=now.year, created_at__month=now.month)),
        )
        
        total_donations = donation_stats['total_donations']
        total_amount = donation_stats['total_amount'] or 0
        recurring_donations = donation_stats['recurring_donations']
        this_month_amount = donation_stats['this_month_amount'] or 0
        
        return {
            'total_donations': total_donations,
            'total_donation_amount': float(total_amount),
            'avg_donation': float(total_amount / total_donations) if total_donations > 0 else 0,
            'recurring_donations': recurring_donations,
            'this_month_donations': float(this_month_amount),
        }
    
    def get_chart_data(self):
        """Prepare data for all charts"""
        return {
            'monthly_user_growth': self.get_monthly_user_growth(),
            'user_status_distribution': self.get_user_status_distribution(),
            'event_status_distribution': self.get_event_status_distribution(),
            'monthly_event_creation': self.get_monthly_event_creation(),
            'registrations_by_event': self.get_registrations_by_event(),
            'capacity_vs_booked': self.get_capacity_vs_booked(),
            'donation_trend': self.get_donation_trend(),
            'users_by_community': self.get_user_by_community(),
            'events_by_type': self.get_event_by_type(),
            'activity_timeline': self.get_activity_timeline(),
            'registration_trend': self.get_registrations_by_event(),  # Alias for template
            'donations_by_month': self.get_donation_trend(),  # Alias for template
        }
    
    def get_monthly_user_growth(self):
        """Get monthly user registration growth for last 12 months"""
        months_data = {}
        
        for i in range(11, -1, -1):
            date = timezone.now() - timedelta(days=30*i)
            month_key = date.strftime('%b %Y')
            month_start = date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            count = CustomUser.objects.filter(
                date_joined__gte=month_start,
                date_joined__lt=month_end
            ).count()
            
            months_data[month_key] = count
        
        return {
            'labels': json.dumps(list(months_data.keys())),
            'data': json.dumps(list(months_data.values())),
        }
    
    def get_user_status_distribution(self):
        """Active vs inactive users"""
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        active = CustomUser.objects.filter(last_login__gte=thirty_days_ago).count()
        inactive = CustomUser.objects.filter(
            Q(last_login__lt=thirty_days_ago) | Q(last_login__isnull=True)
        ).count()
        
        return {
            'labels': json.dumps(['Active (30d)', 'Inactive']),
            'data': json.dumps([active, inactive]),
            'backgroundColor': json.dumps(['#10B981', '#EF4444']),
        }
    
    def get_event_status_distribution(self):
        """Event status breakdown"""
        now = timezone.now().date()
        
        upcoming = Program.objects.filter(date__gte=now).count()
        completed = Program.objects.filter(date__lt=now).count()
        
        return {
            'labels': json.dumps(['Upcoming', 'Completed']),
            'data': json.dumps([upcoming, completed]),
            'backgroundColor': json.dumps(['#3B82F6', '#9CA3AF']),
        }
    
    def get_monthly_event_creation(self):
        """Monthly event creation trend"""
        months_data = {}
        
        for i in range(11, -1, -1):
            date = timezone.now() - timedelta(days=30*i)
            month_key = date.strftime('%b %Y')
            month_start = date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            count = Program.objects.filter(
                date__gte=month_start,
                date__lt=month_end
            ).count()
            
            months_data[month_key] = count
        
        return {
            'labels': json.dumps(list(months_data.keys())),
            'data': json.dumps(list(months_data.values())),
        }
    
    def get_registrations_by_event(self):
        """Registration counts for top 10 events"""
        events = Program.objects.annotate(
            registration_count=Count('registrations')
        ).order_by('-registration_count')[:10]
        
        return {
            'labels': json.dumps([event.title[:30] for event in events]),
            'data': json.dumps([event.registration_count for event in events]),
            'backgroundColor': json.dumps(['#8B5CF6'] * len(events)),
        }
    
    def get_capacity_vs_booked(self):
        """Capacity vs booked seats (simulated - adjust based on your capacity field)"""
        # This assumes a maximum capacity estimate based on registrations
        events = Program.objects.annotate(
            booked=Count('registrations')
        ).order_by('-booked')[:8]
        
        return {
            'labels': json.dumps([event.title[:25] for event in events]),
            'booked': json.dumps([event.booked for event in events]),
            'capacity': json.dumps([max(event.booked + 10, 50) for event in events]),  # Estimate
        }
    
    def get_donation_trend(self):
        """Monthly donation trend"""
        months_data = {}
        
        for i in range(11, -1, -1):
            date = timezone.now() - timedelta(days=30*i)
            month_key = date.strftime('%b %Y')
            month_start = date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            total = Donation.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            months_data[month_key] = float(total)
        
        return {
            'labels': json.dumps(list(months_data.keys())),
            'data': json.dumps(list(months_data.values())),
        }
    
    def get_user_by_community(self):
        """User distribution across communities"""
        communities = Community.objects.annotate(
            user_count=Count('primary_members')
        ).order_by('-user_count')[:10]
        
        return {
            'labels': json.dumps([c.name for c in communities]),
            'data': json.dumps([c.user_count for c in communities]),
        }
    
    def get_event_by_type(self):
        """Event distribution by type"""
        events = Program.objects.values('event_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        type_names = {
            'cultural': 'Cultural',
            'workshop': 'Workshop',
            'meeting': 'Meeting',
            'festival': 'Festival',
            'other': 'Other'
        }
        
        return {
            'labels': json.dumps([type_names.get(e['event_type'], e['event_type']) for e in events]),
            'data': json.dumps([e['count'] for e in events]),
            'backgroundColor': json.dumps([
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'
            ][:len(events) if len(events) > 0 else 1]),
        }
    
    def get_activity_timeline(self):
        """Recent activities across platform"""
        today = timezone.now().date()
        activities = []
        
        # Recent event registrations
        recent_registrations = EventRegistration.objects.select_related(
            'user', 'program'
        ).order_by('-registered_at')[:3]
        
        for reg in recent_registrations:
            activities.append({
                'type': 'registration',
                'user': reg.user.get_full_name() if reg.user else reg.guest_name,
                'description': f'Registered for {reg.program.title}',
                'timestamp': reg.registered_at.strftime('%H:%M'),
                'icon': 'event',
            })
        
        # Recent donations
        # Optimized: select_related('user') to prevent N+1 when accessing donation.user
        recent_donations = Donation.objects.select_related('user').order_by('-created_at')[:3]
        for donation in recent_donations:
            user_name = 'Anonymous' if donation.anonymous else (donation.user.get_full_name() if donation.user else 'Guest')
            activities.append({
                'type': 'donation',
                'user': user_name,
                'description': f'Made a donation',
                'amount': str(donation.amount),
                'timestamp': donation.created_at.strftime('%H:%M'),
                'icon': 'favorite',
            })
        
        # Recent requests
        # Optimized: select_related('requester') to prevent N+1 when accessing req.requester
        recent_requests = RequestEvent.objects.select_related('requester').order_by('-submitted_at')[:2]
        for req in recent_requests:
            requester = req.requester.get_full_name() if req.requester else req.requester_name
            activities.append({
                'type': 'request',
                'user': requester,
                'description': f'Requested event: {req.title}',
                'timestamp': req.submitted_at.strftime('%H:%M'),
                'icon': 'add_circle',
            })
        
        # Recent contacts
        recent_contacts = ContactMessage.objects.order_by('-created_at')[:2]
        for contact in recent_contacts:
            activities.append({
                'type': 'contact',
                'user': contact.name,
                'description': f'Sent message: {contact.subject}',
                'timestamp': contact.created_at.strftime('%H:%M'),
                'icon': 'mail',
            })
        
        # Sort by timestamp (most recent first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return activities[:10]


# ============================================
# ADVANCED ADMIN PANEL
# ============================================


@user_passes_test(staff_required, login_url='login')
@cache_page(300)  # Cache for 5 minutes
def advanced_admin_panel(request):
    """Advanced admin panel for managing all aspects of the community"""
    context = {
        'total_users': CustomUser.objects.count(),
        'total_events': Program.objects.count(),
        'total_announcements': Announcement.objects.count(),
        'total_faqs': FAQ.objects.count(),
    }
    return render(request, 'dashboard/legacy/admin.html', context)
