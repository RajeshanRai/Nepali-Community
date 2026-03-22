from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum, Q, Avg, Case, When, IntegerField, Max, F, Prefetch
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from datetime import timedelta, datetime, date, time
import json
import csv

from core.email_utils import (
    send_notification_email,
    build_branded_email_html,
    build_event_newsletter_html,
    build_security_alert_html,
)
from users.models import CustomUser
from programs.models import Program, EventRegistration, RequestEvent
from donations.models import Donation
from communities.models import Community
from contacts.models import ContactMessage
from partners.models import Partner
from core.models import TeamMember
from volunteers.models import VolunteerApplication, VolunteerOpportunity, VolunteerRequest
from announcements.models import Announcement
from dashboard.models import MemberModerationAction, AdminNotificationState
from faqs.models import FAQ, FAQCategory
from .forms import (
    ProgramForm, RequestEventForm, VolunteerOpportunityForm,
    AnnouncementForm, FAQForm, DonationForm, ContactMessageForm, CommunityForm, PartnerForm, TeamMemberForm,
    AdminProfileForm, AdminPasswordForm,
)
from .utils import (
    normalize_activity_datetime,
    get_dashboard_notifications,
    get_month_date_range,
    get_months_ago,
    get_sidebar_counts,
    is_ajax_request,
    success_json_response,
)
from .decorators import staff_required, superuser_required


def _active_member_emails():
    return list(
        CustomUser.objects.filter(is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )


def admin_required(view_func):
    """Decorator to require superuser status"""
    def wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_superuser):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapped_view


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin for class‑based views that restricts access to active superusers.
    """
    login_url = 'login'

    def test_func(self):
        return staff_required(self.request.user)


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
# ADVANCED ADMIN PANEL - FULL CRUD INTERFACE
# ============================================


@user_passes_test(staff_required, login_url='login')
@cache_page(300)  # Cache for 5 minutes
def advanced_admin_panel(request):
    """Advanced admin panel for managing all aspects of the community"""
    context = {
        'total_events': Program.objects.count(),
        'total_volunteers': VolunteerApplication.objects.count(),
        'pending_requests': RequestEvent.objects.filter(status='pending').count(),
        'total_announcements': Announcement.objects.count(),
        'total_faqs': FAQ.objects.count(),
        'total_users': CustomUser.objects.count(),
        
        # Detailed data for each section - OPTIMIZED with select_related to prevent N+1 queries
        'events': Program.objects.select_related('community').order_by('-date')[:10],
        'volunteer_opportunities': VolunteerOpportunity.objects.select_related('created_by').order_by('-created_at')[:10],
        'volunteer_applications': VolunteerApplication.objects.select_related('opportunity', 'applicant', 'reviewed_by').order_by('-applied_at')[:10],
        'volunteer_requests': VolunteerRequest.objects.all().order_by('-created_at')[:10],
        'event_requests': RequestEvent.objects.select_related('requester', 'community', 'approved_by').order_by('-submitted_at')[:10],
        'announcements': Announcement.objects.select_related('created_by').order_by('-created_at')[:10],
        'faqs': FAQ.objects.select_related('category', 'created_by').order_by('-created_at')[:10],
        'users': CustomUser.objects.all().order_by('-date_joined')[:10],
    }
    return render(request, 'dashboard/admin/admin.html', context)


# ====== EVENT MANAGEMENT ======
@user_passes_test(staff_required, login_url='login')
def event_list(request):
    """List all events"""
    events = Program.objects.all().order_by('date', 'id')
    search = request.GET.get('search', '')
    if search:
        events = events.filter(Q(title__icontains=search) | Q(description__icontains=search))
    return render(request, 'dashboard/events/list.html', {'events': events, 'search': search})


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def event_create(request):
    """Create new event"""
    if request.method == 'POST':
        form = ProgramForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save()
            send_notification_email(
                subject=f'New Event: {event.title}',
                message=(
                    f"A new event has been published.\n\n"
                    f"Title: {event.title}\n"
                    f"Date: {event.date}\n"
                    f"Location: {event.location or 'TBA'}\n"
                ),
                recipients=_active_member_emails(),
                html_message=build_event_newsletter_html(
                    title='A New Community Event Is Live',
                    greeting='Hello Community Member,',
                    summary='A new event is now open for registrations.',
                    event_name=event.title,
                    event_date=event.date.strftime('%B %d, %Y'),
                    venue_text=event.location or 'Venue details will be shared shortly.',
                    category_text=event.get_event_type_display() if hasattr(event, 'get_event_type_display') else (event.event_type or 'Community Event'),
                    detail_points=[
                        'Reserve your place early to avoid missing this session.',
                        'Invite your friends and family to join the community event.',
                    ],
                ),
            )
            messages.success(request, f'Event "{event.title}" has been created successfully.')
            return redirect('dashboard:event_list')
    else:
        form = ProgramForm()
    return render(request, 'dashboard/events/form.html', {'form': form, 'title': 'Create Event'})


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def event_edit(request, pk):
    """Edit event"""
    event = get_object_or_404(Program, pk=pk)
    if request.method == 'POST':
        form = ProgramForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            updated_event = form.save()
            send_update_email = request.POST.get('send_update_email') == 'on'
            if send_update_email:
                send_notification_email(
                    subject=f'Event Updated: {updated_event.title}',
                    message=(
                        f"An event has been updated.\n\n"
                        f"Title: {updated_event.title}\n"
                        f"Date: {updated_event.date}\n"
                        f"Location: {updated_event.location or 'TBA'}\n"
                    ),
                    recipients=_active_member_emails(),
                    html_message=build_event_newsletter_html(
                        title='Community Event Updated',
                        greeting='Hello Community Member,',
                        summary=f"Important updates were made to {updated_event.title}.",
                        event_name=updated_event.title,
                        event_date=updated_event.date.strftime('%B %d, %Y'),
                        venue_text=updated_event.location or 'Venue details will be shared shortly.',
                        category_text=updated_event.get_event_type_display() if hasattr(updated_event, 'get_event_type_display') else (updated_event.event_type or 'Community Event'),
                        detail_points=[
                            'Please review the latest event details before attending.',
                            'Your registration remains valid if you already signed up.',
                        ],
                    ),
                )
                messages.success(request, f'Event "{event.title}" has been updated and members were notified.')
            else:
                messages.success(request, f'Event "{event.title}" has been updated without sending an email update.')
            return redirect('dashboard:event_list')
    else:
        form = ProgramForm(instance=event)
    return render(request, 'dashboard/events/form.html', {'form': form, 'event': event, 'title': 'Edit Event'})


@user_passes_test(staff_required, login_url='login')
def event_delete(request, pk):
    """Delete event"""
    event = get_object_or_404(Program, pk=pk)
    if request.method == 'POST':
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        event_title = event.title
        event.delete()
        success_message = f'Event "{event_title}" has been deleted successfully.'
        
        if is_ajax:
            return JsonResponse({'message': success_message})
        else:
            messages.success(request, success_message)
            return redirect('dashboard:event_list')
    
    return render(request, 'dashboard/events/confirm_delete.html', {'event': event})


# ====== VOLUNTEER MANAGEMENT ======
@user_passes_test(staff_required, login_url='login')
def volunteer_opportunities_list(request):
    """List all volunteer opportunities"""
    opportunities = VolunteerOpportunity.objects.all().order_by('-created_at')
    search = request.GET.get('search', '')
    selected_status = request.GET.get('status', '').strip()

    if selected_status:
        opportunities = opportunities.filter(status=selected_status)

    if search:
        opportunities = opportunities.filter(Q(title__icontains=search) | Q(description__icontains=search))

    status_options = [
        {
            'value': value,
            'label': label,
            'selected': value == selected_status,
        }
        for value, label in VolunteerOpportunity.STATUS_CHOICES
    ]

    context = {
        'opportunities': opportunities,
        'search': search,
        'selected_status': selected_status,
        'status_options': status_options,
    }
    return render(request, 'dashboard/volunteers/opportunities_list.html', context)


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def volunteer_opportunity_create(request):
    """Create new volunteer opportunity"""
    if request.method == 'POST':
        form = VolunteerOpportunityForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard:volunteer_opportunities_list')
    else:
        form = VolunteerOpportunityForm()
    return render(request, 'dashboard/volunteers/opportunity_form.html', {'form': form, 'title': 'Create Volunteer Opportunity'})


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def volunteer_opportunity_edit(request, pk):
    """Edit volunteer opportunity"""
    opportunity = get_object_or_404(VolunteerOpportunity, pk=pk)
    if request.method == 'POST':
        form = VolunteerOpportunityForm(request.POST, instance=opportunity)
        if form.is_valid():
            form.save()
            return redirect('dashboard:volunteer_opportunities_list')
    else:
        form = VolunteerOpportunityForm(instance=opportunity)
    return render(request, 'dashboard/volunteers/opportunity_form.html', {'form': form, 'opportunity': opportunity, 'title': 'Edit Volunteer Opportunity'})


@user_passes_test(staff_required, login_url='login')
def volunteer_opportunity_delete(request, pk):
    """Delete volunteer opportunity"""
    opportunity = get_object_or_404(VolunteerOpportunity, pk=pk)
    if request.method == 'POST':
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        opportunity_title = opportunity.title
        opportunity.delete()
        success_message = f'Volunteer opportunity "{opportunity_title}" has been deleted successfully.'
        
        if is_ajax:
            return JsonResponse({'message': success_message})
        else:
            messages.success(request, success_message)
            return redirect('dashboard:volunteer_opportunities_list')
    
    return render(request, 'dashboard/volunteers/confirm_delete.html', {'opportunity': opportunity})


@user_passes_test(staff_required, login_url='login')
def volunteer_applications_list(request):
    """List all volunteer applications"""
    applications = VolunteerApplication.objects.all().order_by('-applied_at')
    volunteer_requests = VolunteerRequest.objects.select_related('assigned_opportunity').all().order_by('-created_at')
    available_opportunities = VolunteerOpportunity.objects.filter(
        status='open',
        positions_needed__gt=F('positions_filled')
    ).order_by('title')
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)

    context = {
        'applications': applications,
        'volunteer_requests': volunteer_requests,
        'available_opportunities': available_opportunities,
        'status_filter': status_filter,
        # sidebar counts are provided by the global context processor
    }
    return render(request, 'dashboard/volunteers/applications.html', context)


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def volunteer_application_approve(request, pk):
    """Accept volunteer application"""
    application = get_object_or_404(VolunteerApplication, pk=pk)
    application.status = 'accepted'
    application.save()
    
    # Update volunteer opportunity positions
    opportunity = application.opportunity
    opportunity.positions_filled = VolunteerApplication.objects.filter(
        opportunity=opportunity, status__in=['accepted', 'assigned']
    ).count()
    
    if opportunity.positions_filled >= opportunity.positions_needed:
        opportunity.status = 'filled'
    
    opportunity.save()

    send_notification_email(
        subject=f'Volunteer application accepted: {opportunity.title}',
        message=(
            f"Hi {application.name},\n\n"
            f"Your volunteer application has been accepted.\n"
            f"Opportunity: {opportunity.title}\n"
            f"Category: {opportunity.get_category_display()}\n"
            f"Start Date: {opportunity.start_date or 'TBA'}\n"
            f"Time Commitment: {opportunity.time_commitment or 'TBA'}\n\n"
            "Thank you for volunteering with us."
        ),
        recipients=[application.email],
        html_message=build_branded_email_html(
            title='Volunteer Application Accepted',
            greeting=f'Hi {application.name},',
            intro=f"Great news, your application for {opportunity.title} has been accepted.",
            paragraphs=[
                f"You are joining the {opportunity.get_category_display()} stream, and we are excited to have your support.",
                f"Your expected start window is {opportunity.start_date or 'to be announced'}, with a commitment pattern of {opportunity.time_commitment or 'to be confirmed'}.",
            ],
        ),
    )
    
    return JsonResponse({'success': True, 'message': 'Application accepted'})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def volunteer_application_reject(request, pk):
    """Reject volunteer application"""
    application = get_object_or_404(VolunteerApplication, pk=pk)
    application.status = 'rejected'
    application.save()
    return JsonResponse({'success': True, 'message': 'Application rejected'})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def volunteer_application_delete(request, pk):
    """Delete volunteer application"""
    application = get_object_or_404(VolunteerApplication, pk=pk)
    opportunity = application.opportunity

    application.delete()

    assigned_count = VolunteerApplication.objects.filter(
        opportunity=opportunity,
        status__in=['accepted', 'assigned']
    ).count()
    opportunity.positions_filled = assigned_count

    if assigned_count < opportunity.positions_needed and opportunity.status == 'filled':
        opportunity.status = 'open'

    opportunity.save(update_fields=['positions_filled', 'status'])
    return JsonResponse({'success': True, 'message': 'Application deleted'})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def volunteer_application_assign(request, pk):
    """Assign accepted volunteer application to a program"""
    application = get_object_or_404(VolunteerApplication, pk=pk)
    
    if application.status != 'accepted':
        return JsonResponse({'success': False, 'message': 'Only accepted applications can be assigned'})
    
    # Get the opportunity ID from POST data
    opportunity_id = request.POST.get('opportunity_id')
    if not opportunity_id:
        return JsonResponse({'success': False, 'message': 'Opportunity ID is required'})
    
    try:
        opportunity = VolunteerOpportunity.objects.get(pk=opportunity_id)
    except VolunteerOpportunity.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Opportunity not found'})
    
    # Update application status
    application.status = 'assigned'
    application.admin_notes = f'Assigned to opportunity: {opportunity.title} (ID: {opportunity.id})'
    application.save()
    
    # Update positions for the new opportunity
    opportunity.positions_filled = VolunteerApplication.objects.filter(
        opportunity=opportunity, status__in=['accepted', 'assigned']
    ).count()
    
    if opportunity.positions_filled >= opportunity.positions_needed:
        opportunity.status = 'filled'
    
    opportunity.save()
    
    return JsonResponse({'success': True, 'message': f'Application assigned to {opportunity.title}'})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def volunteer_request_approve(request, pk):
    """Approve volunteer request by marking it accepted"""
    volunteer_request = get_object_or_404(VolunteerRequest, pk=pk)
    volunteer_request.status = 'accepted'
    volunteer_request.reviewed_at = timezone.now()
    volunteer_request.save(update_fields=['status', 'reviewed_at'])
    return JsonResponse({'success': True, 'message': 'Volunteer request accepted'})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def volunteer_request_reject(request, pk):
    """Reject volunteer request by closing it"""
    volunteer_request = get_object_or_404(VolunteerRequest, pk=pk)
    volunteer_request.status = 'closed'
    volunteer_request.reviewed_at = timezone.now()
    volunteer_request.save(update_fields=['status', 'reviewed_at'])
    return JsonResponse({'success': True, 'message': 'Volunteer request rejected'})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def volunteer_request_delete(request, pk):
    """Delete volunteer request"""
    volunteer_request = get_object_or_404(VolunteerRequest, pk=pk)
    volunteer_request.delete()
    return JsonResponse({'success': True, 'message': 'Volunteer request deleted'})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def volunteer_request_assign(request, pk):
    """Assign general volunteer request to a volunteer opportunity"""
    volunteer_request = get_object_or_404(VolunteerRequest, pk=pk)

    if volunteer_request.status not in ['accepted', 'contacted', 'assigned']:
        return JsonResponse({'success': False, 'message': 'Request must be accepted before assigning.'}, status=400)

    opportunity_id = request.POST.get('opportunity_id')

    if not opportunity_id:
        return JsonResponse({'success': False, 'message': 'Opportunity is required.'}, status=400)

    opportunity = get_object_or_404(VolunteerOpportunity, pk=opportunity_id)

    # Keep previous assignment state so we can release old slot if reassigned.
    previous_opportunity = volunteer_request.assigned_opportunity

    existing_target_application = VolunteerApplication.objects.filter(
        opportunity=opportunity,
        email__iexact=volunteer_request.email,
    ).first()

    assigned_count_qs = VolunteerApplication.objects.filter(
        opportunity=opportunity,
        status__in=['accepted', 'assigned']
    )
    if existing_target_application:
        assigned_count_qs = assigned_count_qs.exclude(pk=existing_target_application.pk)
    assigned_count = assigned_count_qs.count()

    target_is_current = bool(previous_opportunity and previous_opportunity.pk == opportunity.pk)
    if not target_is_current and (opportunity.status != 'open' or assigned_count >= opportunity.positions_needed):
        return JsonResponse({'success': False, 'message': 'Selected opportunity is not available.'}, status=400)

    application, created = VolunteerApplication.objects.get_or_create(
        opportunity=opportunity,
        email=volunteer_request.email,
        defaults={
            'name': volunteer_request.name,
            'phone': volunteer_request.phone,
            'motivation': volunteer_request.purpose,
            'experience': volunteer_request.expertise or '',
            'availability': volunteer_request.schedule_availability,
            'status': 'assigned',
            'reviewed_at': timezone.now(),
            'reviewed_by': request.user,
            'admin_notes': f'Assigned from volunteer request #{volunteer_request.id}',
        }
    )

    if not created:
        application.name = volunteer_request.name
        application.phone = volunteer_request.phone
        application.motivation = volunteer_request.purpose
        application.experience = volunteer_request.expertise or ''
        application.availability = volunteer_request.schedule_availability
        application.status = 'assigned'
        application.reviewed_at = timezone.now()
        application.reviewed_by = request.user
        application.admin_notes = f'Assigned from volunteer request #{volunteer_request.id}'
        application.save()

    # If reassigned to a different opportunity, release previous slot for this volunteer.
    if previous_opportunity and previous_opportunity.pk != opportunity.pk:
        previous_application = VolunteerApplication.objects.filter(
            opportunity=previous_opportunity,
            email__iexact=volunteer_request.email,
            status__in=['accepted', 'assigned']
        ).first()
        if previous_application:
            previous_application.status = 'withdrawn'
            previous_application.reviewed_at = timezone.now()
            previous_application.reviewed_by = request.user
            previous_application.admin_notes = (
                f'Reassigned from opportunity #{previous_opportunity.pk} to #{opportunity.pk} '
                f'via volunteer request #{volunteer_request.id}'
            )
            previous_application.save(update_fields=['status', 'reviewed_at', 'reviewed_by', 'admin_notes'])

    volunteer_request.status = 'assigned'
    volunteer_request.assigned_opportunity = opportunity
    volunteer_request.reviewed_at = timezone.now()
    volunteer_request.admin_notes = (
        f'Assigned to opportunity "{opportunity.title}" (ID: {opportunity.id}) by {request.user.username}'
    )
    volunteer_request.save(update_fields=['status', 'assigned_opportunity', 'reviewed_at', 'admin_notes'])

    # Recompute previous opportunity counters/status after reassignment.
    if previous_opportunity and previous_opportunity.pk != opportunity.pk:
        previous_opportunity.positions_filled = VolunteerApplication.objects.filter(
            opportunity=previous_opportunity,
            status__in=['accepted', 'assigned']
        ).count()
        previous_opportunity.status = (
            'filled' if previous_opportunity.positions_filled >= previous_opportunity.positions_needed else 'open'
        )
        previous_opportunity.save(update_fields=['positions_filled', 'status'])

    opportunity.positions_filled = VolunteerApplication.objects.filter(
        opportunity=opportunity,
        status__in=['accepted', 'assigned']
    ).count()

    if opportunity.positions_filled >= opportunity.positions_needed:
        opportunity.status = 'filled'
    else:
        opportunity.status = 'open'

    opportunity.save(update_fields=['positions_filled', 'status'])

    return JsonResponse({
        'success': True,
        'message': f'Volunteer assigned to {opportunity.title} successfully.',
        'application_id': application.id,
    })


# ====== EVENT REQUEST MANAGEMENT ======
@user_passes_test(staff_required, login_url='login')
def event_requests_list(request):
    """List all event requests"""
    requests = RequestEvent.objects.all().order_by('-submitted_at')
    status_filter = request.GET.get('status', '').strip()

    # Allow case-insensitive filtering to avoid missing records if status values are not normalized
    if status_filter:
        requests = requests.filter(status__iexact=status_filter)

    return render(request, 'dashboard/requests/list.html', {'requests': requests, 'status_filter': status_filter})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def event_request_approve(request, pk):
    """Approve event request and create a Program"""
    try:
        event_request = get_object_or_404(RequestEvent, pk=pk)
        
        # Validate that community exists before creating program
        if not event_request.community:
            return JsonResponse({
                'success': False, 
                'message': 'Cannot approve request without a community. Please assign a community to this request.'
            }, status=400)
        
        # Create program from request
        program = Program.objects.create(
            title=event_request.title,
            description=event_request.description,
            date=event_request.date or timezone.now().date(),
            location=event_request.location,
            event_type=event_request.event_type,
            community=event_request.community,
        )
        
        # Update request status
        event_request.status = 'approved'
        event_request.created_program = program
        event_request.approved_by = request.user
        event_request.approved_at = timezone.now()
        event_request.save()

        send_notification_email(
            subject=f'New Event: {program.title}',
            message=(
                f"A new event has been published.\n\n"
                f"Title: {program.title}\n"
                f"Date: {program.date}\n"
                f"Location: {program.location or 'TBA'}\n"
            ),
            recipients=_active_member_emails(),
            html_message=build_event_newsletter_html(
                title='A New Community Event Is Available',
                greeting='Hello Community Member,',
                summary='A newly approved event is now available for community registration.',
                event_name=program.title,
                event_date=program.date.strftime('%B %d, %Y'),
                venue_text=program.location or 'Venue details will be shared shortly.',
                category_text=program.get_event_type_display() if hasattr(program, 'get_event_type_display') else (program.event_type or 'Community Event'),
                detail_points=[
                    'Early registration is encouraged so we can plan seating and resources well.',
                    'Share this update with your network to support participation.',
                ],
            ),
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Request approved and program created successfully',
            'program_id': program.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error approving request: {str(e)}'
        }, status=500)


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def event_request_reject(request, pk):
    """Reject event request"""
    try:
        event_request = get_object_or_404(RequestEvent, pk=pk)
        
        # Get rejection reason from POST data (FormData from JavaScript)
        rejection_reason = request.POST.get('reason', '')
        
        # Update request status
        event_request.status = 'rejected'
        if rejection_reason:
            event_request.rejection_reason = rejection_reason
        event_request.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Request rejected successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error rejecting request: {str(e)}'
        }, status=500)


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def event_request_delete(request, pk):
    """Delete an event request"""
    event_request = get_object_or_404(RequestEvent, pk=pk)
    request_title = event_request.title
    event_request.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f'Request "{request_title}" deleted successfully.'})

    messages.success(request, f'Request "{request_title}" deleted successfully.')
    return redirect('dashboard:projects_rejected')


# ====== ANNOUNCEMENT MANAGEMENT ======
@user_passes_test(staff_required, login_url='login')
def announcements_list(request):
    """List all announcements"""
    announcements = Announcement.objects.all().order_by('-created_at')
    search = request.GET.get('search', '')
    selected_category = request.GET.get('category', '').strip()

    if selected_category:
        announcements = announcements.filter(category=selected_category)

    if search:
        announcements = announcements.filter(Q(title__icontains=search) | Q(content__icontains=search))

    category_options = [
        {
            'value': value,
            'label': label,
            'selected': value == selected_category,
        }
        for value, label in Announcement.CATEGORY_CHOICES
    ]

    context = {
        'announcements': announcements,
        'search': search,
        'selected_category': selected_category,
        'category_options': category_options,
    }
    return render(request, 'dashboard/announcements/list.html', context)


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def announcement_create(request):
    """Create new announcement"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            if announcement.is_active:
                send_notification_email(
                    subject=f'New Announcement: {announcement.title}',
                    message=(
                        f"A new announcement was posted.\n\n"
                        f"Title: {announcement.title}\n"
                        f"Category: {announcement.get_category_display()}\n"
                        f"Priority: {announcement.get_priority_display()}\n\n"
                        f"{announcement.content[:500]}"
                    ),
                    recipients=_active_member_emails(),
                    html_message=build_branded_email_html(
                        title='New Community Announcement',
                        greeting='Hello Community Member,',
                        intro=f"A new announcement titled {announcement.title} has been published.",
                        paragraphs=[
                            f"This update is categorized under {announcement.get_category_display()} with {announcement.get_priority_display()} priority.",
                            announcement.content[:500],
                        ],
                    ),
                )
            return redirect('dashboard:announcements_list')
    else:
        form = AnnouncementForm()
    return render(request, 'dashboard/announcements/form.html', {'form': form, 'title': 'Create Announcement'})


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def announcement_edit(request, pk):
    """Edit announcement"""
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            updated = form.save()
            send_update_email = request.POST.get('send_update_email') == 'on'
            if updated.is_active and send_update_email:
                send_notification_email(
                    subject=f'Announcement Updated: {updated.title}',
                    message=(
                        f"An announcement has been updated.\n\n"
                        f"Title: {updated.title}\n"
                        f"Category: {updated.get_category_display()}\n"
                        f"Priority: {updated.get_priority_display()}\n"
                    ),
                    recipients=_active_member_emails(),
                    html_message=build_branded_email_html(
                        title='Announcement Updated',
                        greeting='Hello Community Member,',
                        intro=f"An announcement has been updated: {updated.title}.",
                        paragraphs=[
                            f"The update remains in {updated.get_category_display()} and is currently marked as {updated.get_priority_display()} priority.",
                            'Please review the latest details in your dashboard.',
                        ],
                    ),
                )
                messages.success(request, 'Announcement updated and members were notified.')
            elif not updated.is_active:
                messages.success(request, 'Announcement updated. No update email sent because it is not active.')
            else:
                messages.success(request, 'Announcement updated without sending an email update.')
            return redirect('dashboard:announcements_list')
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, 'dashboard/announcements/form.html', {'form': form, 'announcement': announcement, 'title': 'Edit Announcement'})


@user_passes_test(staff_required, login_url='login')
def announcement_delete(request, pk):
    """Delete announcement"""
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        announcement_title = announcement.title
        announcement.delete()
        success_message = f'Announcement "{announcement_title}" has been deleted successfully.'
        
        if is_ajax:
            return JsonResponse({'message': success_message})
        else:
            messages.success(request, success_message)
            return redirect('dashboard:announcements_list')
    
    return render(request, 'dashboard/announcements/confirm_delete.html', {'announcement': announcement})


# ====== FAQ MANAGEMENT ======
@user_passes_test(staff_required, login_url='login')
def faqs_list(request):
    """List all FAQs"""
    faqs = FAQ.objects.all().order_by('-created_at')
    search = request.GET.get('search', '')
    selected_category = request.GET.get('category', '').strip()

    if selected_category:
        faqs = faqs.filter(category__slug=selected_category)

    if search:
        faqs = faqs.filter(Q(question__icontains=search) | Q(answer__icontains=search))

    categories = FAQCategory.objects.all()
    category_options = [
        {
            'slug': category.slug,
            'name': category.name,
            'selected': category.slug == selected_category,
        }
        for category in categories
    ]

    context = {
        'faqs': faqs,
        'search': search,
        'selected_category': selected_category,
        'categories': categories,
        'category_options': category_options,
    }
    return render(request, 'dashboard/faqs/list.html', context)


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def faq_create(request):
    """Create new FAQ"""
    if request.method == 'POST':
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard:faqs_list')
    else:
        form = FAQForm()
    return render(request, 'dashboard/faqs/form.html', {'form': form, 'title': 'Create FAQ'})


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def faq_edit(request, pk):
    """Edit FAQ"""
    faq = get_object_or_404(FAQ, pk=pk)
    if request.method == 'POST':
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            return redirect('dashboard:faqs_list')
    else:
        form = FAQForm(instance=faq)
    return render(request, 'dashboard/faqs/form.html', {'form': form, 'faq': faq, 'title': 'Edit FAQ'})


@user_passes_test(staff_required, login_url='login')
def faq_delete(request, pk):
    """Delete FAQ"""
    faq = get_object_or_404(FAQ, pk=pk)
    if request.method == 'POST':
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        faq_question = faq.question
        faq.delete()
        success_message = f'FAQ "{faq_question}" has been deleted successfully.'
        
        if is_ajax:
            return JsonResponse({'message': success_message})
        else:
            messages.success(request, success_message)
            return redirect('dashboard:faqs_list')
    
    return render(request, 'dashboard/faqs/confirm_delete.html', {'faq': faq})


# ====== DONATION MANAGEMENT ======

class DonationListView(StaffRequiredMixin, ListView):
    model = Donation
    template_name = 'dashboard/donations/list.html'
    context_object_name = 'donations'
    paginate_by = 25

    def _safe_redirect_target(self):
        redirect_target = self.request.POST.get('return_to', '').strip()
        if redirect_target.startswith('/'):
            return redirect_target
        return reverse('dashboard:donations_list')

    def _base_queryset(self):
        qs = Donation.objects.select_related('user')

        search = self.request.GET.get('search', '').strip()
        selected_status = self.request.GET.get('status', '').strip()
        selected_method = self.request.GET.get('method', '').strip()
        selected_recurring = self.request.GET.get('recurring', '').strip()
        selected_anonymous = self.request.GET.get('anonymous', '').strip()
        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()

        if selected_status:
            qs = qs.filter(status=selected_status)
        if selected_method:
            qs = qs.filter(payment_method=selected_method)
        if selected_recurring in {'true', 'false'}:
            qs = qs.filter(is_recurring=(selected_recurring == 'true'))
        if selected_anonymous in {'true', 'false'}:
            qs = qs.filter(anonymous=(selected_anonymous == 'true'))
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if search:
            qs = qs.filter(
                Q(donor_name__icontains=search)
                | Q(donor_email__icontains=search)
                | Q(donor_phone__icontains=search)
                | Q(donor_address_line1__icontains=search)
                | Q(donor_city__icontains=search)
                | Q(donor_province__icontains=search)
                | Q(donor_postal_code__icontains=search)
                | Q(transaction_ref__icontains=search)
                | Q(purpose__icontains=search)
                | Q(stripe_session_id__icontains=search)
                | Q(stripe_payment_intent_id__icontains=search)
            )
        return qs

    def get_queryset(self):
        qs = self._base_queryset()
        sort_option = self.request.GET.get('sort', '-created_at').strip()
        sort_map = {
            '-created_at': '-created_at',
            'created_at': 'created_at',
            '-amount': '-amount',
            'amount': 'amount',
            'status': 'status',
            'payment_method': 'payment_method',
        }
        return qs.order_by(sort_map.get(sort_option, '-created_at'))

    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'csv':
            return self._export_csv()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '').strip()
        if action == 'update_status':
            donation_id = request.POST.get('donation_id')
            new_status = request.POST.get('new_status', '').strip()
            donation = get_object_or_404(Donation, pk=donation_id)
            valid_statuses = {status for status, _ in Donation.DONATION_STATUS}
            if new_status in valid_statuses:
                donation.status = new_status
                donation.save(update_fields=['status'])
                messages.success(request, f'Donation #{donation.pk} status updated to {donation.get_status_display()}.')
            else:
                messages.error(request, 'Invalid status selected.')
            return redirect(self._safe_redirect_target())

        if action.startswith('bulk_'):
            selected_ids = request.POST.getlist('selected_donations')
            if not selected_ids:
                messages.warning(request, 'Select at least one donation for bulk action.')
                return redirect(self._safe_redirect_target())

            selected_qs = Donation.objects.filter(pk__in=selected_ids)
            selected_count = selected_qs.count()

            if action == 'bulk_mark_completed':
                selected_qs.update(status='completed')
                messages.success(request, f'{selected_count} donation(s) marked as Completed.')
            elif action == 'bulk_mark_pending':
                selected_qs.update(status='pending')
                messages.success(request, f'{selected_count} donation(s) marked as Pending.')
            elif action == 'bulk_mark_failed':
                selected_qs.update(status='failed')
                messages.success(request, f'{selected_count} donation(s) marked as Failed.')
            elif action == 'bulk_delete':
                selected_qs.delete()
                messages.success(request, f'{selected_count} donation(s) deleted successfully.')
            else:
                messages.error(request, 'Unsupported bulk action.')
            return redirect(self._safe_redirect_target())

        messages.error(request, 'Invalid action request.')
        return redirect(self._safe_redirect_target())

    def _export_csv(self):
        qs = self._base_queryset().order_by('-created_at')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dashboard_donations.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID',
            'Date',
            'Donor Name',
            'Donor Email',
            'Donor Phone',
            'Donor Address',
            'Donor City',
            'Donor Province',
            'Donor Postal Code',
            'Amount',
            'Purpose',
            'Payment Method',
            'Status',
            'Recurring',
            'Anonymous',
            'Card Last 4',
            'Transaction Ref',
            'Stripe Session',
            'Stripe Payment Intent',
        ])

        for donation in qs:
            writer.writerow([
                donation.pk,
                donation.created_at.strftime('%Y-%m-%d %H:%M'),
                donation.donor_name or (donation.user.username if donation.user else ''),
                donation.donor_email,
                donation.donor_phone,
                donation.donor_address_line1,
                donation.donor_city,
                donation.donor_province,
                donation.donor_postal_code,
                donation.amount,
                donation.purpose,
                donation.get_payment_method_display(),
                donation.get_status_display(),
                'Yes' if donation.is_recurring else 'No',
                'Yes' if donation.anonymous else 'No',
                donation.card_last_four,
                donation.transaction_ref,
                donation.stripe_session_id,
                donation.stripe_payment_intent_id,
            ])
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_qs = self._base_queryset()
        filtered_totals = filtered_qs.aggregate(total_amount=Sum('amount'))
        completed_totals = filtered_qs.filter(status='completed').aggregate(total_amount=Sum('amount'))
        overall_totals = Donation.objects.aggregate(total_amount=Sum('amount'))

        current_query = self.request.GET.copy()
        if 'page' in current_query:
            current_query.pop('page')

        context.update({
            'search': self.request.GET.get('search', '').strip(),
            'selected_status': self.request.GET.get('status', '').strip(),
            'selected_method': self.request.GET.get('method', '').strip(),
            'selected_recurring': self.request.GET.get('recurring', '').strip(),
            'selected_anonymous': self.request.GET.get('anonymous', '').strip(),
            'date_from': self.request.GET.get('date_from', '').strip(),
            'date_to': self.request.GET.get('date_to', '').strip(),
            'selected_sort': self.request.GET.get('sort', '-created_at').strip(),
            'status_choices': Donation.DONATION_STATUS,
            'method_choices': Donation.PAYMENT_METHOD_CHOICES,
            'filtered_count': filtered_qs.count(),
            'filtered_amount_total': filtered_totals['total_amount'] or 0,
            'completed_amount_total': completed_totals['total_amount'] or 0,
            'pending_count': filtered_qs.filter(status='pending').count(),
            'failed_count': filtered_qs.filter(status='failed').count(),
            'recurring_count': filtered_qs.filter(is_recurring=True).count(),
            'card_count': filtered_qs.filter(payment_method='card').count(),
            'overall_count': Donation.objects.count(),
            'overall_amount_total': overall_totals['total_amount'] or 0,
            'active_filters_count': sum(
                1
                for value in [
                    self.request.GET.get('search', '').strip(),
                    self.request.GET.get('status', '').strip(),
                    self.request.GET.get('method', '').strip(),
                    self.request.GET.get('recurring', '').strip(),
                    self.request.GET.get('anonymous', '').strip(),
                    self.request.GET.get('date_from', '').strip(),
                    self.request.GET.get('date_to', '').strip(),
                ]
                if value
            ),
            'current_query': current_query.urlencode(),
        })
        return context


class DonationCreateView(StaffRequiredMixin, CreateView):
    model = Donation
    form_class = DonationForm
    template_name = 'dashboard/donations/form.html'
    success_url = reverse_lazy('dashboard:donations_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Donation #{self.object.pk} created successfully.')
        return response


class DonationUpdateView(StaffRequiredMixin, UpdateView):
    model = Donation
    form_class = DonationForm
    template_name = 'dashboard/donations/form.html'
    success_url = reverse_lazy('dashboard:donations_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Donation #{self.object.pk} updated successfully.')
        return response


class DonationDeleteView(StaffRequiredMixin, DeleteView):
    model = Donation
    template_name = 'dashboard/donations/confirm_delete.html'
    success_url = reverse_lazy('dashboard:donations_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        donation_id = self.object.pk
        if is_ajax_request(request):
            self.object.delete()
            return success_json_response(f'Donation #{donation_id} deleted successfully.')
        messages.success(request, f'Donation #{donation_id} deleted successfully.')
        return super().delete(request, *args, **kwargs)


# compatibility wrappers for function-style imports
# these are used by urls and __init__.py to maintain existing names

donations_list = DonationListView.as_view()
donation_create = DonationCreateView.as_view()
donation_edit = DonationUpdateView.as_view()
donation_delete = DonationDeleteView.as_view()



# ====== PARTNER MANAGEMENT ======

class PartnerListView(StaffRequiredMixin, ListView):
    model = Partner
    template_name = 'dashboard/partners/list.html'
    context_object_name = 'partners'
    ordering = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(website__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.object_list
        context['search'] = self.request.GET.get('search', '').strip()
        context['total_partners'] = qs.count()
        context['with_website_count'] = qs.exclude(website='').count()
        context['with_logo_count'] = qs.filter(logo__isnull=False).exclude(logo='').count()
        context['with_social_count'] = qs.exclude(social_links={}).count()
        return context


class PartnerCreateView(StaffRequiredMixin, CreateView):
    model = Partner
    form_class = PartnerForm
    template_name = 'dashboard/partners/form.html'
    success_url = reverse_lazy('dashboard:partners_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Partner "{self.object.name}" created successfully.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Partner'
        return context


class PartnerUpdateView(StaffRequiredMixin, UpdateView):
    model = Partner
    form_class = PartnerForm
    template_name = 'dashboard/partners/form.html'
    success_url = reverse_lazy('dashboard:partners_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Partner "{self.object.name}" updated successfully.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Partner'
        return context


class PartnerDeleteView(StaffRequiredMixin, DeleteView):
    model = Partner
    template_name = 'dashboard/partners/confirm_delete.html'
    success_url = reverse_lazy('dashboard:partners_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        partner_name = self.object.name
        if is_ajax_request(request):
            self.object.delete()
            return success_json_response(f'Partner "{partner_name}" deleted successfully.')
        messages.success(request, f'Partner "{partner_name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


# compatibility wrappers for function-style imports
partners_list = PartnerListView.as_view()
partner_create = PartnerCreateView.as_view()
partner_edit = PartnerUpdateView.as_view()
partner_delete = PartnerDeleteView.as_view()



# ====== TEAM MEMBER MANAGEMENT ======

class TeamMemberListView(StaffRequiredMixin, ListView):
    model = TeamMember
    template_name = 'dashboard/team_members/list.html'
    context_object_name = 'team_members'
    ordering = ['order', 'name']

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('search', '').strip()
        status = self.request.GET.get('status', '').strip().lower()

        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(role__icontains=search)
                | Q(focus__icontains=search)
                | Q(email__icontains=search)
            )

        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_members = TeamMember.objects.all()
        context['search'] = self.request.GET.get('search', '').strip()
        context['status'] = self.request.GET.get('status', '').strip().lower()
        context['total_members'] = all_members.count()
        context['active_members'] = all_members.filter(is_active=True).count()
        context['inactive_members'] = all_members.filter(is_active=False).count()
        context['with_photo_count'] = all_members.filter(photo__isnull=False).exclude(photo='').count()
        return context


class TeamMemberCreateView(StaffRequiredMixin, CreateView):
    model = TeamMember
    form_class = TeamMemberForm
    template_name = 'dashboard/team_members/form.html'
    success_url = reverse_lazy('dashboard:team_members_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Team member "{self.object.name}" created successfully.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Team Member'
        return context


class TeamMemberUpdateView(StaffRequiredMixin, UpdateView):
    model = TeamMember
    form_class = TeamMemberForm
    template_name = 'dashboard/team_members/form.html'
    success_url = reverse_lazy('dashboard:team_members_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Team member "{self.object.name}" updated successfully.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Team Member'
        return context


class TeamMemberDeleteView(StaffRequiredMixin, DeleteView):
    model = TeamMember
    template_name = 'dashboard/team_members/confirm_delete.html'
    success_url = reverse_lazy('dashboard:team_members_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        member_name = self.object.name
        if is_ajax_request(request):
            self.object.delete()
            return success_json_response(f'Team member "{member_name}" deleted successfully.')
        messages.success(request, f'Team member "{member_name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


team_members_list = TeamMemberListView.as_view()
team_member_create = TeamMemberCreateView.as_view()
team_member_edit = TeamMemberUpdateView.as_view()
team_member_delete = TeamMemberDeleteView.as_view()



# ====== CONTACT MESSAGE MANAGEMENT ======
@user_passes_test(staff_required, login_url='login')
def contact_messages_list(request):
    """List all contact messages"""
    messages_qs = ContactMessage.objects.all().order_by('-created_at')
    search = request.GET.get('search', '')

    if search:
        messages_qs = messages_qs.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(subject__icontains=search)
            | Q(message__icontains=search)
        )

    context = {
        'contact_messages': messages_qs,
        'search': search,
    }
    return render(request, 'dashboard/contacts/list.html', context)


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def contact_message_create(request):
    """Create contact message record"""
    if request.method == 'POST':
        form = ContactMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message_obj = form.save()
            messages.success(request, f'Contact message #{message_obj.pk} created successfully.')
            return redirect('dashboard:contact_messages_list')
        else:
            # Handle validation errors
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = ContactMessageForm()
    return render(request, 'dashboard/contacts/form.html', {'form': form, 'title': 'Create Contact Message'})


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def contact_message_edit(request, pk):
    """Edit contact message record"""
    message_obj = get_object_or_404(ContactMessage, pk=pk)
    if request.method == 'POST':
        form = ContactMessageForm(request.POST, request.FILES, instance=message_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Contact message #{message_obj.pk} updated successfully.')
            return redirect('dashboard:contact_messages_list')
        else:
            # Handle validation errors
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = ContactMessageForm(instance=message_obj)
    return render(request, 'dashboard/contacts/form.html', {'form': form, 'message_obj': message_obj, 'title': 'Edit Contact Message'})


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def contact_message_delete(request, pk):
    """Delete contact message record"""
    message_obj = get_object_or_404(ContactMessage, pk=pk)
    if request.method == 'POST':
        message_id = message_obj.pk
        message_obj.delete()
        messages.success(request, f'Contact message #{message_id} deleted successfully.')
        return redirect('dashboard:contact_messages_list')
    return render(request, 'dashboard/contacts/confirm_delete.html', {'message_obj': message_obj})

# ============================================
# SIDEBAR ADMIN INTERFACE - NEW ADMIN PANEL
# ============================================


@user_passes_test(staff_required, login_url='login')
def admin_overview(request):
    """Main admin dashboard overview with stats, charts, and recent activity"""
    today = timezone.now().date()
    
    # Stats
    total_projects = Program.objects.count()
    pending_projects = RequestEvent.objects.filter(status='pending').count()
    approved_projects = Program.objects.count()
    rejected_projects = RequestEvent.objects.filter(status='rejected').count()
    completed_projects = Program.objects.filter(date__lt=today).count()
    
    total_volunteers = VolunteerOpportunity.objects.count()
    active_volunteers = VolunteerOpportunity.objects.filter(status='open').count()
    
    total_users = CustomUser.objects.count()
    
    # Category data for pie chart
    categories = Community.objects.all()[:5]
    category_labels = [cat.name for cat in categories]
    category_data = [Program.objects.filter(community=cat).count() for cat in categories]
    
    # Volunteer growth data (last 6 months)
    volunteer_months = []
    volunteer_new_data = []
    volunteer_active_data = []
    
    for i in range(6):
        month_date = timezone.now() - timedelta(days=30*i)
        month_name = month_date.strftime('%b')
        volunteer_months.insert(0, month_name)
        volunteer_new_data.insert(0, VolunteerOpportunity.objects.filter(
            created_at__month=month_date.month,
            created_at__year=month_date.year
        ).count())
        volunteer_active_data.insert(0, VolunteerOpportunity.objects.filter(
            status='open',
            created_at__lte=month_date
        ).count())
    
    # Projects monthly data (last 6 months)
    project_months = []
    project_monthly_data = []
    
# build project months data using utility helpers that correctly
    # handle calendar months instead of naive 30‑day approximations
    for i in range(6):
        month_start, month_end = get_month_date_range(i)
        month_name = month_start.strftime('%b %Y')
        project_months.insert(0, month_name)
        project_monthly_data.insert(0, Program.objects.filter(
            date__range=(month_start, month_end)
        ).count())

    # normalize_activity_datetime is defined once in dashboard.utils and
    # imported at the top of this module; local duplicate removed.

    # CRUD management cards covering major project modules
    module_crud_cards = [
        {
            'title': 'Programs & Events',
            'icon': 'fas fa-calendar-alt',
            'count': Program.objects.count(),
            'description': 'Create and manage community programs.',
            'links': [
                {'label': 'Create', 'url': reverse('dashboard:event_create')},
                {'label': 'Read', 'url': reverse('dashboard:projects_all')},
                {'label': 'Update/Delete', 'url': reverse('dashboard:projects_all')},
            ]
        },
        {
            'title': 'Event Requests',
            'icon': 'fas fa-inbox',
            'count': RequestEvent.objects.count(),
            'description': 'Review, approve, and process incoming requests.',
            'links': [
                {'label': 'Pending', 'url': reverse('dashboard:event_requests_list')},
                {'label': 'Approve', 'url': reverse('dashboard:projects_pending')},
                {'label': 'Reject', 'url': reverse('dashboard:projects_rejected')},
            ]
        },
        {
            'title': 'Volunteers',
            'icon': 'fas fa-hands-helping',
            'count': VolunteerOpportunity.objects.count(),
            'description': 'Track opportunities and volunteer participation.',
            'links': [
                {'label': 'Create', 'url': reverse('dashboard:volunteer_opportunity_create')},
                {'label': 'Read', 'url': reverse('dashboard:volunteers_all')},
                {'label': 'Update/Delete', 'url': reverse('dashboard:volunteer_opportunities_list')},
            ]
        },
        {
            'title': 'Volunteer Applications',
            'icon': 'fas fa-file-signature',
            'count': VolunteerApplication.objects.count(),
            'description': 'Handle approvals and rejections for applications.',
            'links': [
                {'label': 'Read', 'url': reverse('dashboard:volunteers_applications')},
                {'label': 'Approve/Reject', 'url': reverse('dashboard:volunteer_applications_list')},
                {'label': 'Manage', 'url': reverse('dashboard:admin_activity')},
            ]
        },
        {
            'title': 'Announcements',
            'icon': 'fas fa-bullhorn',
            'count': Announcement.objects.count(),
            'description': 'Publish and maintain community announcements.',
            'links': [
                {'label': 'Create', 'url': reverse('dashboard:announcement_create')},
                {'label': 'Read', 'url': reverse('dashboard:announcements_list')},
                {'label': 'Update/Delete', 'url': reverse('dashboard:announcements_list')},
            ]
        },
        {
            'title': 'FAQs',
            'icon': 'fas fa-question-circle',
            'count': FAQ.objects.count(),
            'description': 'Maintain frequently asked questions and answers.',
            'links': [
                {'label': 'Create', 'url': reverse('dashboard:faq_create')},
                {'label': 'Read', 'url': reverse('dashboard:faqs_list')},
                {'label': 'Update/Delete', 'url': reverse('dashboard:faqs_list')},
            ]
        },
        {
            'title': 'Categories',
            'icon': 'fas fa-tags',
            'count': Community.objects.count(),
            'description': 'Organize projects and content categories.',
            'links': [
                {'label': 'Create', 'url': reverse('dashboard:category_create')},
                {'label': 'Read', 'url': reverse('dashboard:categories_list')},
                {'label': 'Update/Delete', 'url': reverse('dashboard:categories_list')},
            ]
        },
        {
            'title': 'Users',
            'icon': 'fas fa-user-shield',
            'count': CustomUser.objects.count(),
            'description': 'Manage members, roles, and account status.',
            'links': [
                {'label': 'Read', 'url': reverse('dashboard:users_all')},
                {'label': 'Roles', 'url': reverse('dashboard:users_roles')},
                {'label': 'Manage', 'url': reverse('dashboard:admin_overview')},
            ]
        },
        {
            'title': 'Donations',
            'icon': 'fas fa-hand-holding-heart',
            'count': Donation.objects.count(),
            'description': 'Track donation records and contributor activity.',
            'links': [
                {'label': 'Create', 'url': reverse('dashboard:donation_create')},
                {'label': 'Read', 'url': reverse('dashboard:donations_list')},
                {'label': 'Update/Delete', 'url': reverse('dashboard:donations_list')},
            ]
        },
        {
            'title': 'Partners',
            'icon': 'fas fa-handshake',
            'count': Partner.objects.count(),
            'description': 'Manage partner profiles shown on the public directory.',
            'links': [
                {'label': 'Create', 'url': reverse('dashboard:partner_create')},
                {'label': 'Read', 'url': reverse('dashboard:partners_list')},
                {'label': 'Update/Delete', 'url': reverse('dashboard:partners_list')},
            ]
        },
        {
            'title': 'Contact Messages',
            'icon': 'fas fa-envelope-open-text',
            'count': ContactMessage.objects.count(),
            'description': 'Review and respond to inbound contact requests.',
            'links': [
                {'label': 'Create', 'url': reverse('dashboard:contact_message_create')},
                {'label': 'Read', 'url': reverse('dashboard:contact_messages_list')},
                {'label': 'Update/Delete', 'url': reverse('dashboard:contact_messages_list')},
            ]
        },
    ]

    # Recent activity stream
    activities = []

    for event in Program.objects.select_related('community').order_by('-date')[:6]:
        activity_date = normalize_activity_datetime(event.date)
        activities.append({
            'actor': 'Program Team',
            'action': f'Program updated: {event.title}',
            'created_at': activity_date,
            'status': 'completed' if event.date < today else 'approved',
            'status_label': 'Completed' if event.date < today else 'Active',
        })

    for req in RequestEvent.objects.select_related('requester').order_by('-submitted_at')[:6]:
        requester_name = req.requester.get_full_name() if req.requester else req.requester_name
        activities.append({
            'actor': requester_name or 'Community Member',
            'action': f'Event request submitted: {req.title}',
            'created_at': normalize_activity_datetime(req.submitted_at),
            'status': req.status,
            'status_label': req.status.title(),
        })

    for app in VolunteerApplication.objects.select_related('applicant', 'opportunity').order_by('-applied_at')[:6]:
        applicant_name = app.applicant.get_full_name() if app.applicant else app.name
        activities.append({
            'actor': applicant_name or 'Volunteer Applicant',
            'action': f'Applied for: {app.opportunity.title}',
            'created_at': normalize_activity_datetime(app.applied_at),
            'status': app.status,
            'status_label': app.status.title(),
        })

    for post in Announcement.objects.order_by('-created_at')[:4]:
        activities.append({
            'actor': 'Announcements Team',
            'action': f'Announcement published: {post.title}',
            'created_at': normalize_activity_datetime(post.created_at),
            'status': 'approved',
            'status_label': 'Published',
        })

    for activity in activities:
        raw_status = (activity.get('status') or 'pending')
        if not isinstance(raw_status, str):
            raw_status = str(raw_status)
        status_class = raw_status.strip().lower() or 'pending'

        status_label = activity.get('status_label')
        if not status_label:
            status_label = status_class.replace('_', ' ').title()

        activity['status_class'] = status_class
        activity['status_display'] = status_label

    recent_activities = sorted(
        activities,
        key=lambda activity: activity['created_at'],
        reverse=True,
    )[:10]
    
    context = {
        'total_projects': total_projects,
        'pending_projects': pending_projects,
        'approved_projects': approved_projects,
        'rejected_projects': rejected_projects,
        'completed_projects': completed_projects,
        'total_volunteers': total_volunteers,
        'active_volunteers': active_volunteers,
        'total_users': total_users,
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'volunteer_months': json.dumps(volunteer_months),
        'volunteer_new_data': json.dumps(volunteer_new_data),
        'volunteer_active_data': json.dumps(volunteer_active_data),
        'project_months': json.dumps(project_months),
        'project_monthly_data': json.dumps(project_monthly_data),
        'recent_activities': recent_activities,
        'module_crud_cards': module_crud_cards,
        'total_event_requests': RequestEvent.objects.count(),
        'total_applications': VolunteerApplication.objects.count(),
        'total_announcements': Announcement.objects.count(),
        'total_faqs': FAQ.objects.count(),
        
        # sidebar counts are injected via context processor
    }
    
    return render(request, 'dashboard/admin_overview.html', context)


@user_passes_test(staff_required, login_url='login')
def admin_analytics(request):
    """Analytics page with detailed charts and statistics"""
    today = timezone.now().date()

    # Monthly trend series for the last 12 months.
    month_labels = []
    monthly_users = []
    monthly_registrations = []
    monthly_volunteer_apps = []
    monthly_donations = []
    monthly_donors = []

    for i in range(12):
        month_start, month_end = get_month_date_range(i)
        month_labels.insert(0, month_start.strftime('%b %Y'))

        monthly_users.insert(0, CustomUser.objects.filter(
            date_joined__date__range=(month_start, month_end)
        ).count())

        monthly_registrations.insert(0, EventRegistration.objects.filter(
            registered_at__date__range=(month_start, month_end)
        ).count())

        monthly_volunteer_apps.insert(0, VolunteerApplication.objects.filter(
            applied_at__date__range=(month_start, month_end)
        ).count())

        monthly_donations.insert(0, float(
            Donation.objects.filter(
                created_at__date__range=(month_start, month_end),
                status='completed',
            ).aggregate(total=Sum('amount'))['total'] or 0
        ))

        monthly_donors.insert(0, Donation.objects.filter(
            created_at__date__range=(month_start, month_end),
            status='completed',
        ).exclude(
            Q(user__isnull=True) & Q(donor_email='')
        ).count())

    # CRM funnel style counts.
    total_users = CustomUser.objects.count()
    users_with_event_registration = CustomUser.objects.filter(eventregistration__isnull=False).distinct().count()
    users_with_volunteer_application = CustomUser.objects.filter(volunteer_applications__isnull=False).distinct().count()
    users_with_donation = CustomUser.objects.filter(donation__isnull=False).distinct().count()

    # Request status distribution.
    request_labels = ['Pending', 'Approved', 'Rejected']
    request_values = [
        RequestEvent.objects.filter(status='pending').count(),
        RequestEvent.objects.filter(status='approved').count(),
        RequestEvent.objects.filter(status='rejected').count(),
    ]

    # Strategic conversion and planning datasets.
    def pct(numerator, denominator):
        if denominator <= 0:
            return 0
        return round((numerator / denominator) * 100, 1)

    conversion_labels = ['User -> Participant', 'Participant -> Volunteer', 'Participant -> Donor']
    conversion_values = [
        pct(users_with_event_registration, total_users),
        pct(users_with_volunteer_application, users_with_event_registration),
        pct(users_with_donation, users_with_event_registration),
    ]

    planning_labels = []
    planning_events = []
    planning_registrations = []

    for i in range(12):
        month_start, month_end = get_month_date_range(-i)
        # get_month_date_range may return datetime values; normalize to date for safe comparisons.
        if hasattr(month_start, 'date'):
            month_start = month_start.date()
        if hasattr(month_end, 'date'):
            month_end = month_end.date()

        planning_labels.append(month_start.strftime('%b %Y'))

        effective_start = max(month_start, today)
        planning_events.append(Program.objects.filter(
            date__range=(effective_start, month_end)
        ).count())

        planning_registrations.append(EventRegistration.objects.filter(
            program__date__range=(effective_start, month_end)
        ).count())

    volunteer_pipeline_labels = ['Pending', 'Approved', 'Rejected', 'Withdrawn']
    volunteer_pipeline_values = [
        VolunteerApplication.objects.filter(status='pending').count(),
        VolunteerApplication.objects.filter(status='approved').count(),
        VolunteerApplication.objects.filter(status='rejected').count(),
        VolunteerApplication.objects.filter(status='withdrawn').count(),
    ]

    # KPI cards with weekly micro-visualization bars.
    def weekly_counts(model, dt_field, weeks=8, extra_filters=None):
        values = []
        now = timezone.now()
        filters = extra_filters or {}
        for week_idx in range(weeks):
            end_dt = now - timedelta(days=7 * week_idx)
            start_dt = end_dt - timedelta(days=6)
            query = {f'{dt_field}__date__range': (start_dt.date(), end_dt.date())}
            query.update(filters)
            values.insert(0, model.objects.filter(**query).count())
        return values

    registrations_weekly = weekly_counts(EventRegistration, 'registered_at')
    volunteer_weekly = weekly_counts(VolunteerApplication, 'applied_at')
    announcements_weekly = weekly_counts(Announcement, 'created_at')
    donations_weekly = weekly_counts(Donation, 'created_at', extra_filters={'status': 'completed'})

    def growth_delta(series):
        if len(series) < 2 or series[-2] == 0:
            if series and series[-1] > 0:
                return 100
            return 0
        return round(((series[-1] - series[-2]) / series[-2]) * 100)

    kpi_cards = [
        {
            'title': 'Event Registrations',
            'value': EventRegistration.objects.count(),
            'delta': growth_delta(registrations_weekly),
            'trend': registrations_weekly,
        },
        {
            'title': 'Volunteer Applications',
            'value': VolunteerApplication.objects.count(),
            'delta': growth_delta(volunteer_weekly),
            'trend': volunteer_weekly,
        },
        {
            'title': 'Announcements Published',
            'value': Announcement.objects.count(),
            'delta': growth_delta(announcements_weekly),
            'trend': announcements_weekly,
        },
        {
            'title': 'Completed Donations',
            'value': Donation.objects.filter(status='completed').count(),
            'delta': growth_delta(donations_weekly),
            'trend': donations_weekly,
        },
    ]

    context = {
        'month_labels': json.dumps(month_labels),
        'monthly_users': json.dumps(monthly_users),
        'monthly_registrations': json.dumps(monthly_registrations),
        'monthly_volunteer_apps': json.dumps(monthly_volunteer_apps),
        'monthly_donations': json.dumps(monthly_donations),
        'monthly_donors': json.dumps(monthly_donors),
        'crm_funnel_labels': json.dumps(['Registered Users', 'Event Participants', 'Volunteer Applicants', 'Donors']),
        'crm_funnel_values': json.dumps([
            total_users,
            users_with_event_registration,
            users_with_volunteer_application,
            users_with_donation,
        ]),
        'conversion_labels': json.dumps(conversion_labels),
        'conversion_values': json.dumps(conversion_values),
        'request_labels': json.dumps(request_labels),
        'request_values': json.dumps(request_values),
        'planning_labels': json.dumps(planning_labels),
        'planning_events': json.dumps(planning_events),
        'planning_registrations': json.dumps(planning_registrations),
        'volunteer_pipeline_labels': json.dumps(volunteer_pipeline_labels),
        'volunteer_pipeline_values': json.dumps(volunteer_pipeline_values),
        'range_presets': json.dumps(['30d', '90d', '6m', '12m']),
        'default_range': '6m',
        'kpi_cards': kpi_cards,
        'active_users_30d': CustomUser.objects.filter(last_login__date__gte=today - timedelta(days=30)).count(),
        'open_volunteer_roles': VolunteerOpportunity.objects.filter(status='open').count(),
        # sidebar counts injected via context processor
    }
    return render(request, 'dashboard/admin_analytics.html', context)


@user_passes_test(staff_required, login_url='login')
def admin_activity(request):
    """Recent activity page showing all system activities"""
    activity_type_meta = {
        'event': {
            'icon': 'calendar-check',
            'label': 'Program',
            'tone': 'sky',
        },
        'application': {
            'icon': 'hands-helping',
            'label': 'Volunteer',
            'tone': 'emerald',
        },
        'request': {
            'icon': 'clipboard-list',
            'label': 'Request',
            'tone': 'amber',
        },
    }

    selected_type = (request.GET.get('type') or 'all').strip().lower()
    if selected_type not in {'all', 'event', 'application', 'request'}:
        selected_type = 'all'

    start_date = None
    end_date = None
    start_date_raw = (request.GET.get('start_date') or '').strip()
    end_date_raw = (request.GET.get('end_date') or '').strip()

    if start_date_raw:
        try:
            start_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date()
        except ValueError:
            start_date = None
            start_date_raw = ''

    if end_date_raw:
        try:
            end_date = datetime.strptime(end_date_raw, '%Y-%m-%d').date()
        except ValueError:
            end_date = None
            end_date_raw = ''

    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date
        start_date_raw = start_date.isoformat()
        end_date_raw = end_date.isoformat()

    # Get recent events, applications, requests (filter-aware)
    recent_events_qs = Program.objects.all()
    recent_applications_qs = VolunteerApplication.objects.all()
    recent_requests_qs = RequestEvent.objects.all()

    if start_date:
        recent_events_qs = recent_events_qs.filter(date__gte=start_date)
        recent_applications_qs = recent_applications_qs.filter(applied_at__date__gte=start_date)
        recent_requests_qs = recent_requests_qs.filter(submitted_at__date__gte=start_date)

    if end_date:
        recent_events_qs = recent_events_qs.filter(date__lte=end_date)
        recent_applications_qs = recent_applications_qs.filter(applied_at__date__lte=end_date)
        recent_requests_qs = recent_requests_qs.filter(submitted_at__date__lte=end_date)

    if selected_type in {'all', 'event'}:
        recent_events = recent_events_qs.order_by('-date')[:60]
    else:
        recent_events = []

    if selected_type in {'all', 'application'}:
        recent_applications = recent_applications_qs.order_by('-applied_at')[:60]
    else:
        recent_applications = []

    if selected_type in {'all', 'request'}:
        recent_requests = recent_requests_qs.order_by('-submitted_at')[:60]
    else:
        recent_requests = []

    # Combine and sort by date
    activities = []
    
    for event in recent_events:
        meta = activity_type_meta['event']
        activities.append({
            'type': 'event',
            'type_label': meta['label'],
            'icon': meta['icon'],
            'tone': meta['tone'],
            'title': f'Event created: {event.title}',
            'date': event.date,
            'user': 'System',
            'has_time': False,
        })
    
    for app in recent_applications:
        meta = activity_type_meta['application']
        activities.append({
            'type': 'application',
            'type_label': meta['label'],
            'icon': meta['icon'],
            'tone': meta['tone'],
            'title': f'Volunteer application: {app.opportunity.title}',
            'date': app.applied_at,
            'user': app.applicant.username if app.applicant else app.name,
            'has_time': True,
        })
    
    for req in recent_requests:
        meta = activity_type_meta['request']
        activities.append({
            'type': 'request',
            'type_label': meta['label'],
            'icon': meta['icon'],
            'tone': meta['tone'],
            'title': f'Event request: {req.title}',
            'date': req.submitted_at,
            'user': req.requester.username if req.requester else req.requester_name,
            'has_time': True,
        })
    
    # Sort by date (normalize mixed date/datetime values)
    def _activity_sort_key(activity):
        value = activity.get('date')
        if isinstance(value, datetime):
            return (value.date(), value.time())
        if isinstance(value, date):
            return (value, time.min)
        return (date.min, time.min)

    activities.sort(key=_activity_sort_key, reverse=True)
    activities = activities[:80]

    today_date = timezone.localdate()
    for activity in activities:
        value = activity.get('date')
        if isinstance(value, datetime):
            activity_day = timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
        elif isinstance(value, date):
            activity_day = value
        else:
            activity_day = date.min
        activity['activity_day'] = activity_day

    type_counts = {
        'event': 0,
        'application': 0,
        'request': 0,
    }
    for activity in activities:
        if activity['type'] in type_counts:
            type_counts[activity['type']] += 1

    today_activities_count = sum(1 for activity in activities if activity.get('activity_day') == today_date)

    filter_range_label = 'All dates'
    if start_date and end_date:
        filter_range_label = f"{start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}"
    elif start_date:
        filter_range_label = f"From {start_date.strftime('%b %d, %Y')}"
    elif end_date:
        filter_range_label = f"Up to {end_date.strftime('%b %d, %Y')}"

    summary_cards = [
        {
            'label': 'Today',
            'value': today_activities_count,
            'icon': 'bolt',
            'tone': 'violet',
            'meta': 'Activities in the last 24 hours',
        },
        {
            'label': 'Programs',
            'value': type_counts['event'],
            'icon': 'calendar-check',
            'tone': 'sky',
            'meta': 'Recent program postings',
        },
        {
            'label': 'Volunteer Apps',
            'value': type_counts['application'],
            'icon': 'hands-helping',
            'tone': 'emerald',
            'meta': 'Volunteer applications received',
        },
        {
            'label': 'Event Requests',
            'value': type_counts['request'],
            'icon': 'clipboard-list',
            'tone': 'amber',
            'meta': 'Community event requests submitted',
        },
    ]
    
    context = {
        'activities': activities,
        'summary_cards': summary_cards,
        'total_activities': len(activities),
        'today_activities_count': today_activities_count,
        'selected_type': selected_type,
        'filter_start_date': start_date_raw,
        'filter_end_date': end_date_raw,
        'filter_range_label': filter_range_label,
        # sidebar counts are injected via context processor
    }
    return render(request, 'dashboard/admin_activity.html', context)


# ====== PROJECT MANAGEMENT VIEWS ======

@user_passes_test(staff_required, login_url='login')
def projects_all(request):
    """All projects listing"""
    projects = Program.objects.all().order_by('-date')
    today = timezone.now().date()
    context = {
        'projects': projects,
        'today': today,
        # sidebar counts are injected via context processor
    }
    return render(request, 'dashboard/projects/all.html', context)


@user_passes_test(staff_required, login_url='login')
def projects_pending(request):
    """Pending projects listing"""
    projects = RequestEvent.objects.filter(status='pending').order_by('-submitted_at')
    context = {
        'projects': projects,
        # sidebar counts are injected via context processor
    }
    return render(request, 'dashboard/projects/pending.html', context)


@user_passes_test(staff_required, login_url='login')
def projects_approved(request):
    """Approved projects listing"""
    projects = Program.objects.all().order_by('-date')
    context = {
        'projects': projects,
        # sidebar counts injected via context processor
    }
    return render(request, 'dashboard/projects/approved.html', context)


@user_passes_test(staff_required, login_url='login')
def projects_rejected(request):
    """Rejected projects listing"""
    projects = RequestEvent.objects.filter(status='rejected').order_by('-submitted_at')
    context = {
        'projects': projects,
        **get_sidebar_counts(request.user),
    }
    return render(request, 'dashboard/projects/rejected.html', context)


# ====== VOLUNTEER MANAGEMENT VIEWS ======

@user_passes_test(staff_required, login_url='login')
def volunteers_all(request):
    """All volunteer opportunities listing"""
    opportunities = (
        VolunteerOpportunity.objects
        .prefetch_related(
            Prefetch(
                'applications',
                queryset=VolunteerApplication.objects.exclude(status='withdrawn').order_by('-applied_at'),
            )
        )
        .order_by('-created_at')
    )
    context = {
        'opportunities': opportunities,
        # sidebar counts are injected via context processor
    }
    return render(request, 'dashboard/volunteers/all.html', context)


@user_passes_test(staff_required, login_url='login')
def volunteers_applications(request):
    """All volunteer applications listing"""
    applications = VolunteerApplication.objects.all().order_by('-applied_at')
    volunteer_requests = VolunteerRequest.objects.all().order_by('-created_at')
    available_opportunities = VolunteerOpportunity.objects.filter(status='open').order_by('title')
    context = {
        'applications': applications,
        'volunteer_requests': volunteer_requests,
        'available_opportunities': available_opportunities,
        # sidebar counts are provided by the global context processor
    }
    return render(request, 'dashboard/volunteers/applications.html', context)


# ====== USER MANAGEMENT VIEWS ======

@user_passes_test(staff_required, login_url='login')
def users_all(request):
    """Member directory and moderation dashboard."""
    search_query = request.GET.get('q', '').strip()
    users = CustomUser.objects.all().order_by('-date_joined')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone_number__icontains=search_query)
        )

    users = users.annotate(
        registration_count=Count('eventregistration', distinct=True),
        created_posts=Count('announcements', distinct=True),
    )

    now = timezone.now()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_end = this_month_start - timedelta(seconds=1)
    prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_members = CustomUser.objects.count()
    active_users = CustomUser.objects.filter(is_active=True).count()
    recent_growth = CustomUser.objects.filter(date_joined__gte=this_month_start).count()
    previous_growth = CustomUser.objects.filter(
        date_joined__gte=prev_month_start,
        date_joined__lte=prev_month_end,
    ).count()

    growth_delta_pct = 0.0
    if previous_growth > 0:
        growth_delta_pct = ((recent_growth - previous_growth) / previous_growth) * 100
    elif recent_growth > 0:
        growth_delta_pct = 100.0

    total_registrations = EventRegistration.objects.count()
    avg_registrations_per_active_user = round(total_registrations / active_users, 2) if active_users else 0
    engagement_rate = round((total_registrations / total_members) * 100, 1) if total_members else 0

    popular_posts = Announcement.objects.order_by('-views_count', '-created_at')[:5]

    growth_points_qs = (
        CustomUser.objects.filter(date_joined__gte=now - timedelta(days=180))
        .annotate(month=TruncMonth('date_joined'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    growth_points = [
        {
            'month': p['month'].strftime('%b %Y'),
            'count': p['count'],
        }
        for p in growth_points_qs
    ]

    recent_moderation_actions = MemberModerationAction.objects.select_related('user', 'created_by')[:8]

    context = {
        'users': users,
        'search_query': search_query,
        'total_members': total_members,
        'active_users': active_users,
        'recent_growth': recent_growth,
        'growth_delta_pct': round(growth_delta_pct, 1),
        'engagement_rate': engagement_rate,
        'avg_registrations_per_active_user': avg_registrations_per_active_user,
        'popular_posts': popular_posts,
        'growth_points': growth_points,
        'recent_moderation_actions': recent_moderation_actions,
        # sidebar counts injected via context processor
    }
    return render(request, 'dashboard/users/all.html', context)


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["GET"])
def user_profile_api(request, user_id):
    """Return member profile details for dashboard modal."""
    user = get_object_or_404(CustomUser, pk=user_id)
    data = {
        'id': user.id,
        'full_name': user.get_full_name() or user.username,
        'username': user.username,
        'email': user.email,
        'phone_number': user.phone_number or 'N/A',
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_verified_member': user.is_verified_member,
        'is_community_rep': user.is_community_rep,
        'primary_community': user.primary_community.name if user.primary_community else 'N/A',
        'secondary_community': user.secondary_community.name if user.secondary_community else 'N/A',
        'date_joined': user.date_joined.strftime('%b %d, %Y'),
        'last_login': user.last_login.strftime('%b %d, %Y %H:%M') if user.last_login else 'Never',
        'registration_count': user.eventregistration_set.count(),
        'posts_count': user.announcements.count(),
    }
    return JsonResponse({'success': True, 'user': data})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def user_toggle_ban(request, user_id):
    """Toggle member active status as ban/unban action."""
    target_user = get_object_or_404(CustomUser, pk=user_id)

    if target_user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Superuser cannot be banned.'}, status=400)

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])

    action_type = 'unban' if target_user.is_active else 'ban'
    MemberModerationAction.objects.create(
        user=target_user,
        action=action_type,
        reason=request.POST.get('reason', '').strip(),
        created_by=request.user,
    )

    if target_user.email:
        send_notification_email(
            subject='Account status update',
            message=(
                f"Hi {target_user.get_full_name() or target_user.username},\n\n"
                f"Your account status was updated by the admin team.\n"
                f"Current status: {'Active' if target_user.is_active else 'Suspended'}\n\n"
                "If you believe this is a mistake, contact support."
            ),
            recipients=[target_user.email],
            html_message=build_security_alert_html(
                title='Account Status Update',
                greeting=f"Hi {target_user.get_full_name() or target_user.username},",
                severity_label='Status Change Notice',
                summary=f"Your account status is now {'Active' if target_user.is_active else 'Suspended'}.",
                action_items=[
                    'If this change was expected, no action is required.',
                    'If this appears incorrect, contact support for immediate review.',
                ],
            ),
        )

    return JsonResponse({
        'success': True,
        'message': f"User {'unbanned' if target_user.is_active else 'banned'} successfully.",
        'is_active': target_user.is_active,
    })


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def user_warn(request, user_id):
    """Record a moderation warning for a member."""
    target_user = get_object_or_404(CustomUser, pk=user_id)
    reason = request.POST.get('reason', '').strip() or 'Community guideline warning issued.'

    warning_action = MemberModerationAction.objects.create(
        user=target_user,
        action='warn',
        reason=reason,
        created_by=request.user,
    )

    if target_user.email:
        send_notification_email(
            subject='Account warning notice',
            message=(
                f"Hi {target_user.get_full_name() or target_user.username},\n\n"
                "A warning has been issued on your account.\n"
                f"Reason: {reason}\n\n"
                "Please follow community guidelines to avoid restrictions."
            ),
            recipients=[target_user.email],
            html_message=build_security_alert_html(
                title='Account Warning Notice',
                greeting=f"Hi {target_user.get_full_name() or target_user.username},",
                severity_label='Warning',
                summary='A warning was issued on your account following moderation review.',
                action_items=[
                    reason,
                    'Please follow community guidelines to avoid further restrictions.',
                ],
            ),
        )

    warned_at_local = timezone.localtime(warning_action.created_at)
    return JsonResponse({
        'success': True,
        'message': 'Warning recorded successfully.',
        'warned_at_iso': warned_at_local.isoformat(),
        'warned_at_display': warned_at_local.strftime('%b %d, %Y %I:%M %p'),
    })


@user_passes_test(staff_required, login_url='login')
def users_roles(request):
    """User roles and permissions management"""
    users = CustomUser.objects.annotate(
        registration_count=Count('eventregistration', distinct=True),
        last_warned_at=Max('moderation_actions__created_at', filter=Q(moderation_actions__action='warn')),
    ).order_by('-date_joined')

    total_users = users.count()
    superusers_count = users.filter(is_superuser=True).count()
    staff_count = users.filter(is_staff=True, is_superuser=False).count()
    members_count = users.filter(is_staff=False, is_superuser=False).count()
    verified_count = users.filter(is_verified_member=True).count()
    community_rep_count = users.filter(is_community_rep=True).count()
    inactive_count = users.filter(is_active=False).count()

    context = {
        'users': users,
        'total_users': total_users,
        'superusers_count': superusers_count,
        'staff_count': staff_count,
        'members_count': members_count,
        'verified_count': verified_count,
        'community_rep_count': community_rep_count,
        'inactive_count': inactive_count,
        # sidebar counts injected via context processor
    }
    return render(request, 'dashboard/users/roles.html', context)


# ====== CATEGORIES MANAGEMENT ======

@user_passes_test(staff_required, login_url='login')
def categories_list(request):
    """Categories listing"""
    categories = Community.objects.all().order_by('name')
    context = {
        'categories': categories,
        # sidebar counts injected via context processor
    }
    return render(request, 'dashboard/categories/list.html', context)


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def category_create(request):
    """Create category"""
    if request.method == 'POST':
        form = CommunityForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully.')
            return redirect('dashboard:categories_list')
        else:
            # Handle validation errors - ensure form is re-rendered with errors
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = CommunityForm()

    return render(request, 'dashboard/categories/form.html', {
        'form': form,
        'title': 'Create Category',
    })


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def category_edit(request, pk):
    """Edit category"""
    category = get_object_or_404(Community, pk=pk)

    if request.method == 'POST':
        form = CommunityForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('dashboard:categories_list')
        else:
            # Handle validation errors
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CommunityForm(instance=category)

    return render(request, 'dashboard/categories/form.html', {
        'form': form,
        'category': category,
        'title': 'Edit Category',
    })


@require_http_methods(['GET', 'POST'])
@user_passes_test(staff_required, login_url='login')
def category_delete(request, pk):
    """Delete category"""
    category = get_object_or_404(Community, pk=pk)
    
    # Check if category has related programs or committees
    programs_count = category.programs.count()
    committees_count = category.committees.count()
    total_dependencies = programs_count + committees_count
    
    if request.method == 'POST':
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if total_dependencies > 0:
            error_parts = []
            if programs_count > 0:
                error_parts.append(f'{programs_count} program(s)')
            if committees_count > 0:
                error_parts.append(f'{committees_count} committee(s)')
            error_message = f'Cannot delete this category. It has {" and ".join(error_parts)}. Please reassign or delete those first.'
            
            if is_ajax:
                return JsonResponse({'error': error_message}, status=400)
            else:
                messages.error(request, error_message)
                return redirect('dashboard:categories_list')
        
        category_name = category.name
        category.delete()
        success_message = f'Category "{category_name}" has been deleted successfully.'
        
        if is_ajax:
            return JsonResponse({'message': success_message})
        else:
            messages.success(request, success_message)
            return redirect('dashboard:categories_list')
    
    return render(request, 'dashboard/categories/confirm_delete.html', {
        'category': category,
        'programs_count': programs_count,
        'committees_count': committees_count,
        'total_dependencies': total_dependencies
    })


# ====== REPORTS MANAGEMENT ======

@user_passes_test(staff_required, login_url='login')
def reports_monthly(request):
    """Monthly reports"""
    today = timezone.now().date()

    try:
        selected_year = int(request.GET.get('year', today.year))
    except (TypeError, ValueError):
        selected_year = today.year

    try:
        selected_month = int(request.GET.get('month', today.month))
    except (TypeError, ValueError):
        selected_month = today.month

    if selected_month < 1 or selected_month > 12:
        selected_month = today.month

    if selected_year < 2020 or selected_year > (today.year + 2):
        selected_year = today.year

    month_start = date(selected_year, selected_month, 1)
    if selected_month == 12:
        next_month = date(selected_year + 1, 1, 1)
    else:
        next_month = date(selected_year, selected_month + 1, 1)
    month_end = next_month - timedelta(days=1)

    if selected_month == 1:
        prev_month = 12
        prev_year = selected_year - 1
    else:
        prev_month = selected_month - 1
        prev_year = selected_year
    prev_month_start = date(prev_year, prev_month, 1)
    prev_month_end = month_start - timedelta(days=1)

    def pct(part, whole):
        return round((part / whole) * 100, 1) if whole else 0

    programs_qs = Program.objects.filter(date__gte=month_start, date__lte=month_end)
    registrations_qs = EventRegistration.objects.filter(registered_at__date__gte=month_start, registered_at__date__lte=month_end)
    donations_qs = Donation.objects.filter(created_at__date__gte=month_start, created_at__date__lte=month_end)
    completed_donations_qs = donations_qs.filter(status='completed')
    contacts_qs = ContactMessage.objects.filter(created_at__date__gte=month_start, created_at__date__lte=month_end)
    volunteer_requests_qs = VolunteerRequest.objects.filter(created_at__date__gte=month_start, created_at__date__lte=month_end)
    request_events_qs = RequestEvent.objects.filter(submitted_at__date__gte=month_start, submitted_at__date__lte=month_end)

    total_programs = programs_qs.count()
    virtual_programs = programs_qs.filter(is_virtual=True).count()
    onsite_programs = total_programs - virtual_programs
    total_registrations = registrations_qs.count()
    avg_registrations_per_program = round(total_registrations / total_programs, 1) if total_programs else 0

    completed_donation_count = completed_donations_qs.count()
    completed_donation_amount = completed_donations_qs.aggregate(total=Sum('amount'))['total'] or 0
    recurring_donation_count = completed_donations_qs.filter(is_recurring=True).count()
    recurring_donation_share = pct(recurring_donation_count, completed_donation_count)

    total_contacts = contacts_qs.count()
    total_volunteer_requests = volunteer_requests_qs.count()

    total_event_requests = request_events_qs.count()
    approved_event_requests = request_events_qs.filter(status='approved').count()
    rejected_event_requests = request_events_qs.filter(status='rejected').count()
    pending_event_requests = request_events_qs.filter(status='pending').count()
    event_request_approval_rate = pct(approved_event_requests, approved_event_requests + rejected_event_requests)

    event_type_labels = dict(Program.EVENT_TYPES)
    program_type_summary = list(
        programs_qs.values('event_type').annotate(
            total=Count('id'),
            registrations=Count('registrations'),
        ).order_by('-total', 'event_type')
    )
    for row in program_type_summary:
        row['label'] = event_type_labels.get(row['event_type'], row['event_type'].title())
        row['avg_registrations'] = round(row['registrations'] / row['total'], 1) if row['total'] else 0

    top_programs = programs_qs.annotate(
        registrations_count=Count('registrations')
    ).order_by('-registrations_count', 'date', 'title')[:8]

    registrations_by_day = {
        row['registered_at__date']: row['total']
        for row in registrations_qs.values('registered_at__date').annotate(total=Count('id'))
    }
    donations_by_day = {
        row['created_at__date']: row['total']
        for row in completed_donations_qs.values('created_at__date').annotate(total=Count('id'))
    }
    volunteer_by_day = {
        row['created_at__date']: row['total']
        for row in volunteer_requests_qs.values('created_at__date').annotate(total=Count('id'))
    }

    daily_activity = []
    day_cursor = month_start
    while day_cursor <= month_end:
        daily_activity.append({
            'date': day_cursor,
            'registrations': registrations_by_day.get(day_cursor, 0),
            'donations': donations_by_day.get(day_cursor, 0),
            'volunteer_requests': volunteer_by_day.get(day_cursor, 0),
        })
        day_cursor += timedelta(days=1)

    max_daily_volume = max(
        [row['registrations'] for row in daily_activity] +
        [row['donations'] for row in daily_activity] +
        [row['volunteer_requests'] for row in daily_activity] +
        [1]
    )
    for row in daily_activity:
        row['registrations_width'] = round((row['registrations'] / max_daily_volume) * 100, 1)
        row['donations_width'] = round((row['donations'] / max_daily_volume) * 100, 1)
        row['volunteer_width'] = round((row['volunteer_requests'] / max_daily_volume) * 100, 1)

    month_options = [
        {'value': 1, 'label': 'January'}, {'value': 2, 'label': 'February'}, {'value': 3, 'label': 'March'},
        {'value': 4, 'label': 'April'}, {'value': 5, 'label': 'May'}, {'value': 6, 'label': 'June'},
        {'value': 7, 'label': 'July'}, {'value': 8, 'label': 'August'}, {'value': 9, 'label': 'September'},
        {'value': 10, 'label': 'October'}, {'value': 11, 'label': 'November'}, {'value': 12, 'label': 'December'},
    ]
    year_options = list(range(today.year - 4, today.year + 1))

    selected_month_label = next((opt['label'] for opt in month_options if opt['value'] == selected_month), month_start.strftime('%B'))
    selected_period_label = f"{selected_month_label} {selected_year}"
    prev_period_label = f"{prev_month_start.strftime('%B')} {prev_year}"

    prev_programs_qs = Program.objects.filter(date__gte=prev_month_start, date__lte=prev_month_end)
    prev_registrations_qs = EventRegistration.objects.filter(registered_at__date__gte=prev_month_start, registered_at__date__lte=prev_month_end)
    prev_donations_qs = Donation.objects.filter(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end)
    prev_completed_donations_qs = prev_donations_qs.filter(status='completed')
    prev_contacts_qs = ContactMessage.objects.filter(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end)
    prev_volunteer_requests_qs = VolunteerRequest.objects.filter(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end)
    prev_request_events_qs = RequestEvent.objects.filter(submitted_at__date__gte=prev_month_start, submitted_at__date__lte=prev_month_end)

    prev_total_programs = prev_programs_qs.count()
    prev_total_registrations = prev_registrations_qs.count()
    prev_completed_donation_count = prev_completed_donations_qs.count()
    prev_completed_donation_amount = prev_completed_donations_qs.aggregate(total=Sum('amount'))['total'] or 0
    prev_recurring_donation_count = prev_completed_donations_qs.filter(is_recurring=True).count()
    prev_recurring_donation_share = pct(prev_recurring_donation_count, prev_completed_donation_count)
    prev_total_contacts = prev_contacts_qs.count()
    prev_total_volunteer_requests = prev_volunteer_requests_qs.count()
    prev_total_event_requests = prev_request_events_qs.count()
    prev_approved_event_requests = prev_request_events_qs.filter(status='approved').count()
    prev_rejected_event_requests = prev_request_events_qs.filter(status='rejected').count()
    prev_event_request_approval_rate = pct(prev_approved_event_requests, prev_approved_event_requests + prev_rejected_event_requests)

    def build_change_badge(current_value, previous_value):
        current = float(current_value)
        previous = float(previous_value)
        if previous == 0:
            if current == 0:
                return {'direction': 'flat', 'text': '0.0% vs prev'}
            return {'direction': 'up', 'text': 'New vs prev'}

        delta_pct = ((current - previous) / previous) * 100
        if abs(delta_pct) < 0.05:
            direction = 'flat'
        elif delta_pct > 0:
            direction = 'up'
        else:
            direction = 'down'
        sign = '+' if delta_pct > 0 else ''
        return {'direction': direction, 'text': f"{sign}{round(delta_pct, 1)}% vs prev"}

    comparison_badges = {
        'programs': build_change_badge(total_programs, prev_total_programs),
        'registrations': build_change_badge(total_registrations, prev_total_registrations),
        'donations_count': build_change_badge(completed_donation_count, prev_completed_donation_count),
        'donations_amount': build_change_badge(completed_donation_amount, prev_completed_donation_amount),
        'recurring_share': build_change_badge(recurring_donation_share, prev_recurring_donation_share),
        'contacts': build_change_badge(total_contacts, prev_total_contacts),
        'volunteer_requests': build_change_badge(total_volunteer_requests, prev_total_volunteer_requests),
        'event_requests': build_change_badge(total_event_requests, prev_total_event_requests),
        'approval_rate': build_change_badge(event_request_approval_rate, prev_event_request_approval_rate),
    }

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="monthly_report_{selected_year}_{selected_month:02d}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Monthly Analytics Report'])
        writer.writerow(['Period', selected_period_label])
        writer.writerow([])

        writer.writerow(['Summary Metrics'])
        writer.writerow(['Metric', 'Current', f'Previous ({prev_period_label})', 'Change'])
        writer.writerow(['Programs', total_programs, prev_total_programs, comparison_badges['programs']['text']])
        writer.writerow(['Virtual Programs', virtual_programs, '', ''])
        writer.writerow(['On-site Programs', onsite_programs, '', ''])
        writer.writerow(['Registrations', total_registrations, prev_total_registrations, comparison_badges['registrations']['text']])
        writer.writerow(['Avg Registrations Per Program', avg_registrations_per_program, '', ''])
        writer.writerow(['Completed Donations', completed_donation_count, prev_completed_donation_count, comparison_badges['donations_count']['text']])
        writer.writerow(['Completed Donation Amount', completed_donation_amount, prev_completed_donation_amount, comparison_badges['donations_amount']['text']])
        writer.writerow(['Recurring Donation Share (%)', recurring_donation_share, prev_recurring_donation_share, comparison_badges['recurring_share']['text']])
        writer.writerow(['Contact Messages', total_contacts, prev_total_contacts, comparison_badges['contacts']['text']])
        writer.writerow(['Volunteer Requests', total_volunteer_requests, prev_total_volunteer_requests, comparison_badges['volunteer_requests']['text']])
        writer.writerow(['Event Requests', total_event_requests, prev_total_event_requests, comparison_badges['event_requests']['text']])
        writer.writerow(['Event Request Approval Rate (%)', event_request_approval_rate, prev_event_request_approval_rate, comparison_badges['approval_rate']['text']])
        writer.writerow([])

        writer.writerow(['Program Type Breakdown'])
        writer.writerow(['Type', 'Programs', 'Registrations', 'Avg Registrations'])
        for row in program_type_summary:
            writer.writerow([row['label'], row['total'], row['registrations'], row['avg_registrations']])
        writer.writerow([])

        writer.writerow(['Top Programs by Registrations'])
        writer.writerow(['Program', 'Date', 'Type', 'Registrations'])
        for program in top_programs:
            writer.writerow([
                program.title,
                program.date.isoformat() if program.date else '',
                program.get_event_type_display(),
                program.registrations_count,
            ])
        writer.writerow([])

        writer.writerow(['Daily Activity'])
        writer.writerow(['Date', 'Registrations', 'Donations', 'Volunteer Requests'])
        for row in daily_activity:
            writer.writerow([
                row['date'].isoformat(),
                row['registrations'],
                row['donations'],
                row['volunteer_requests'],
            ])
        return response

    context = {
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_period_label': selected_period_label,
        'prev_period_label': prev_period_label,
        'month_options': month_options,
        'year_options': year_options,
        'total_programs': total_programs,
        'virtual_programs': virtual_programs,
        'onsite_programs': onsite_programs,
        'total_registrations': total_registrations,
        'avg_registrations_per_program': avg_registrations_per_program,
        'completed_donation_count': completed_donation_count,
        'completed_donation_amount': completed_donation_amount,
        'recurring_donation_count': recurring_donation_count,
        'recurring_donation_share': recurring_donation_share,
        'total_contacts': total_contacts,
        'total_volunteer_requests': total_volunteer_requests,
        'total_event_requests': total_event_requests,
        'approved_event_requests': approved_event_requests,
        'rejected_event_requests': rejected_event_requests,
        'pending_event_requests': pending_event_requests,
        'event_request_approval_rate': event_request_approval_rate,
        'program_type_summary': program_type_summary,
        'top_programs': top_programs,
        'daily_activity': daily_activity,
        'comparison_badges': comparison_badges,
        **get_sidebar_counts(request.user),
    }
    return render(request, 'dashboard/reports/monthly.html', context)


@user_passes_test(staff_required, login_url='login')
def reports_volunteers(request):
    """Volunteer activity report"""
    today = timezone.now().date()
    month_start = today.replace(day=1)

    start_date = None
    end_date = None
    start_date_raw = (request.GET.get('start_date') or '').strip()
    end_date_raw = (request.GET.get('end_date') or '').strip()

    if start_date_raw:
        try:
            start_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date()
        except ValueError:
            start_date = None
            start_date_raw = ''

    if end_date_raw:
        try:
            end_date = datetime.strptime(end_date_raw, '%Y-%m-%d').date()
        except ValueError:
            end_date = None
            end_date_raw = ''

    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date
        start_date_raw = start_date.isoformat()
        end_date_raw = end_date.isoformat()

    opportunities_qs = VolunteerOpportunity.objects.all()
    applications_qs = VolunteerApplication.objects.all()
    requests_qs = VolunteerRequest.objects.all()

    if start_date:
        opportunities_qs = opportunities_qs.filter(created_at__date__gte=start_date)
        applications_qs = applications_qs.filter(applied_at__date__gte=start_date)
        requests_qs = requests_qs.filter(created_at__date__gte=start_date)

    if end_date:
        opportunities_qs = opportunities_qs.filter(created_at__date__lte=end_date)
        applications_qs = applications_qs.filter(applied_at__date__lte=end_date)
        requests_qs = requests_qs.filter(created_at__date__lte=end_date)

    def pct(part, whole):
        return round((part / whole) * 100, 1) if whole else 0

    total_opportunities = opportunities_qs.count()
    open_opportunities = opportunities_qs.filter(status='open').count()
    filled_opportunities = opportunities_qs.filter(status='filled').count()
    closed_opportunities = opportunities_qs.filter(status='closed').count()

    positions_totals = opportunities_qs.aggregate(
        total_needed=Sum('positions_needed'),
        total_filled=Sum('positions_filled'),
    )
    total_positions_needed = positions_totals['total_needed'] or 0
    total_positions_filled = positions_totals['total_filled'] or 0
    capacity_fill_rate = pct(total_positions_filled, total_positions_needed)

    total_applications = applications_qs.count()
    pending_applications = applications_qs.filter(status='pending').count()
    approved_applications = applications_qs.filter(status='approved').count()
    rejected_applications = applications_qs.filter(status='rejected').count()
    withdrawn_applications = applications_qs.filter(status='withdrawn').count()
    reviewed_applications = approved_applications + rejected_applications
    application_review_rate = pct(reviewed_applications, total_applications)
    approval_rate = pct(approved_applications, reviewed_applications)

    total_requests = requests_qs.count()
    new_requests = requests_qs.filter(status='new').count()
    reviewed_requests = requests_qs.filter(status='reviewed').count()
    contacted_requests = requests_qs.filter(status='contacted').count()
    closed_requests = requests_qs.filter(status='closed').count()
    request_followup_rate = pct(contacted_requests + closed_requests, total_requests)

    opportunity_status_rows = [
        {'label': 'Open opportunities', 'value': open_opportunities},
        {'label': 'Filled opportunities', 'value': filled_opportunities},
        {'label': 'Closed opportunities', 'value': closed_opportunities},
    ]
    max_opportunity_value = max([row['value'] for row in opportunity_status_rows] + [1])
    for row in opportunity_status_rows:
        row['width'] = round((row['value'] / max_opportunity_value) * 100, 1) if max_opportunity_value else 0

    application_status_rows = [
        {'label': 'Pending', 'value': pending_applications},
        {'label': 'Approved', 'value': approved_applications},
        {'label': 'Rejected', 'value': rejected_applications},
        {'label': 'Withdrawn', 'value': withdrawn_applications},
    ]
    max_application_value = max([row['value'] for row in application_status_rows] + [1])
    for row in application_status_rows:
        row['width'] = round((row['value'] / max_application_value) * 100, 1) if max_application_value else 0

    request_status_rows = [
        {'label': 'New requests', 'value': new_requests},
        {'label': 'Reviewed', 'value': reviewed_requests},
        {'label': 'Contacted', 'value': contacted_requests},
        {'label': 'Closed', 'value': closed_requests},
    ]
    max_request_value = max([row['value'] for row in request_status_rows] + [1])
    for row in request_status_rows:
        row['width'] = round((row['value'] / max_request_value) * 100, 1) if max_request_value else 0

    category_labels = dict(VolunteerOpportunity.CATEGORY_CHOICES)
    category_summary = list(
        opportunities_qs.values('category').annotate(
            total=Count('id'),
            open_count=Count('id', filter=Q(status='open')),
            positions_needed=Sum('positions_needed'),
            positions_filled=Sum('positions_filled'),
        ).order_by('-total', 'category')
    )
    for row in category_summary:
        row['label'] = category_labels.get(row['category'], row['category'].title())
        row['positions_needed'] = row['positions_needed'] or 0
        row['positions_filled'] = row['positions_filled'] or 0
        row['fill_rate'] = pct(row['positions_filled'], row['positions_needed'])

    application_count_filter = Q()
    if start_date:
        application_count_filter &= Q(applications__applied_at__date__gte=start_date)
    if end_date:
        application_count_filter &= Q(applications__applied_at__date__lte=end_date)

    top_opportunities = opportunities_qs.annotate(
        applications_count=Count('applications', filter=application_count_filter)
    ).order_by('-applications_count', '-created_at')[:8]

    recent_applications = applications_qs.select_related('opportunity').order_by('-applied_at')[:10]

    if start_date or end_date:
        monthly_start = (start_date or get_months_ago(5).date()).replace(day=1)
        monthly_end = (end_date or today).replace(day=1)
    else:
        monthly_start = get_months_ago(5).date().replace(day=1)
        monthly_end = month_start

    applications_by_month = {
        row['month'].strftime('%Y-%m'): row['total']
        for row in applications_qs.filter(applied_at__date__gte=monthly_start)
        .annotate(month=TruncMonth('applied_at'))
        .values('month')
        .annotate(total=Count('id'))
        .order_by('month')
        if row['month']
    }
    requests_by_month = {
        row['month'].strftime('%Y-%m'): row['total']
        for row in requests_qs.filter(created_at__date__gte=monthly_start)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Count('id'))
        .order_by('month')
        if row['month']
    }

    month_anchors = []
    anchor = monthly_start
    while anchor <= monthly_end and len(month_anchors) < 24:
        month_anchors.append(anchor)
        anchor = get_months_ago(-1, datetime.combine(anchor, time.min)).date().replace(day=1)

    monthly_activity = []
    for month_anchor in month_anchors:
        month_key = month_anchor.strftime('%Y-%m')
        monthly_activity.append({
            'label': month_anchor.strftime('%b %Y'),
            'applications': applications_by_month.get(month_key, 0),
            'requests': requests_by_month.get(month_key, 0),
        })

    max_monthly_volume = max(
        [row['applications'] for row in monthly_activity] +
        [row['requests'] for row in monthly_activity] +
        [1]
    )
    for row in monthly_activity:
        row['applications_width'] = round((row['applications'] / max_monthly_volume) * 100, 1)
        row['requests_width'] = round((row['requests'] / max_monthly_volume) * 100, 1)

    filter_label = 'All time'
    if start_date and end_date:
        filter_label = f"{start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}"
    elif start_date:
        filter_label = f"From {start_date.strftime('%b %d, %Y')}"
    elif end_date:
        filter_label = f"Up to {end_date.strftime('%b %d, %Y')}"

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="volunteer_analytics.csv"'

        writer = csv.writer(response)
        writer.writerow(['Volunteer Analytics Report'])
        writer.writerow(['Date Filter', filter_label])
        writer.writerow([])

        writer.writerow(['Key Metrics'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Opportunities', total_opportunities])
        writer.writerow(['Open Opportunities', open_opportunities])
        writer.writerow(['Filled Opportunities', filled_opportunities])
        writer.writerow(['Closed Opportunities', closed_opportunities])
        writer.writerow(['Total Positions Needed', total_positions_needed])
        writer.writerow(['Total Positions Filled', total_positions_filled])
        writer.writerow(['Capacity Fill Rate (%)', capacity_fill_rate])
        writer.writerow(['Total Applications', total_applications])
        writer.writerow(['Pending Applications', pending_applications])
        writer.writerow(['Approved Applications', approved_applications])
        writer.writerow(['Rejected Applications', rejected_applications])
        writer.writerow(['Withdrawn Applications', withdrawn_applications])
        writer.writerow(['Application Review Rate (%)', application_review_rate])
        writer.writerow(['Approval Rate (%)', approval_rate])
        writer.writerow(['Total Volunteer Requests', total_requests])
        writer.writerow(['Request Follow-up Rate (%)', request_followup_rate])
        writer.writerow([])

        writer.writerow(['Category Breakdown'])
        writer.writerow(['Category', 'Total Opportunities', 'Open Opportunities', 'Positions Needed', 'Positions Filled', 'Fill Rate (%)'])
        for row in category_summary:
            writer.writerow([
                row['label'],
                row['total'],
                row['open_count'],
                row['positions_needed'],
                row['positions_filled'],
                row['fill_rate'],
            ])

        writer.writerow([])
        writer.writerow(['Top Opportunities'])
        writer.writerow(['Opportunity', 'Status', 'Applications'])
        for opportunity in top_opportunities:
            writer.writerow([
                opportunity.title,
                opportunity.get_status_display(),
                opportunity.applications_count,
            ])

        writer.writerow([])
        writer.writerow(['Monthly Activity'])
        writer.writerow(['Month', 'Applications', 'Volunteer Requests'])
        for month in monthly_activity:
            writer.writerow([month['label'], month['applications'], month['requests']])

        return response

    context = {
        'total_opportunities': total_opportunities,
        'open_opportunities': open_opportunities,
        'filled_opportunities': filled_opportunities,
        'closed_opportunities': closed_opportunities,
        'total_positions_needed': total_positions_needed,
        'total_positions_filled': total_positions_filled,
        'capacity_fill_rate': capacity_fill_rate,
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'approved_applications': approved_applications,
        'rejected_applications': rejected_applications,
        'withdrawn_applications': withdrawn_applications,
        'reviewed_applications': reviewed_applications,
        'application_review_rate': application_review_rate,
        'approval_rate': approval_rate,
        'total_requests': total_requests,
        'new_requests': new_requests,
        'reviewed_requests': reviewed_requests,
        'contacted_requests': contacted_requests,
        'closed_requests': closed_requests,
        'request_followup_rate': request_followup_rate,
        'opportunity_status_rows': opportunity_status_rows,
        'application_status_rows': application_status_rows,
        'request_status_rows': request_status_rows,
        'category_summary': category_summary,
        'top_opportunities': top_opportunities,
        'recent_applications': recent_applications,
        'monthly_activity': monthly_activity,
        'filter_start_date': start_date_raw,
        'filter_end_date': end_date_raw,
        'filter_label': filter_label,
        **get_sidebar_counts(request.user),
    }
    return render(request, 'dashboard/reports/volunteers.html', context)


@user_passes_test(staff_required, login_url='login')
def reports_projects(request):
    """Project success rate report"""
    today = timezone.now().date()

    total_requests = RequestEvent.objects.count()
    pending_requests = RequestEvent.objects.filter(status='pending').count()
    approved_requests = RequestEvent.objects.filter(status='approved').count()
    rejected_requests = RequestEvent.objects.filter(status='rejected').count()
    resolved_requests = approved_requests + rejected_requests

    approved_with_program = RequestEvent.objects.filter(
        status='approved',
        created_program__isnull=False,
    ).count()
    completed_programs = Program.objects.filter(
        request_event__status='approved',
        date__lt=today,
    ).count()
    active_upcoming_programs = Program.objects.filter(
        request_event__status='approved',
        date__gte=today,
    ).count()
    approved_registrations = EventRegistration.objects.filter(
        program__request_event__status='approved'
    ).count()

    def pct(part, whole):
        return round((part / whole) * 100, 1) if whole else 0

    approval_rate = pct(approved_requests, resolved_requests)
    conversion_rate = pct(approved_with_program, approved_requests)
    completion_rate = pct(completed_programs, approved_with_program)
    rejection_rate = pct(rejected_requests, resolved_requests)
    avg_registrations = round(approved_registrations / approved_with_program, 1) if approved_with_program else 0

    outcome_rows = [
        {'label': 'Pending review', 'value': pending_requests},
        {'label': 'Approved requests', 'value': approved_requests},
        {'label': 'Rejected requests', 'value': rejected_requests},
        {'label': 'Converted to programs', 'value': approved_with_program},
        {'label': 'Completed programs', 'value': completed_programs},
    ]
    max_outcome_value = max([row['value'] for row in outcome_rows] + [1])
    for row in outcome_rows:
        row['width'] = round((row['value'] / max_outcome_value) * 100, 1) if max_outcome_value else 0

    event_type_labels = dict(RequestEvent.EVENT_TYPE_CHOICES)
    event_type_summary = list(
        RequestEvent.objects.values('event_type').annotate(
            total=Count('id'),
            approved=Count('id', filter=Q(status='approved')),
            rejected=Count('id', filter=Q(status='rejected')),
        ).order_by('-total', 'event_type')
    )
    for row in event_type_summary:
        row['label'] = event_type_labels.get(row['event_type'], row['event_type'].title())
        row['success_rate'] = pct(row['approved'], row['approved'] + row['rejected'])

    community_summary = list(
        RequestEvent.objects.exclude(community__isnull=True)
        .values('community__name')
        .annotate(
            total=Count('id'),
            approved=Count('id', filter=Q(status='approved')),
        )
        .order_by('-approved', '-total')[:6]
    )
    for row in community_summary:
        row['success_rate'] = pct(row['approved'], row['total'])

    recent_requests = RequestEvent.objects.select_related('community', 'created_program').order_by('-submitted_at')[:8]

    context = {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'approved_with_program': approved_with_program,
        'completed_programs': completed_programs,
        'active_upcoming_programs': active_upcoming_programs,
        'approval_rate': approval_rate,
        'conversion_rate': conversion_rate,
        'completion_rate': completion_rate,
        'rejection_rate': rejection_rate,
        'avg_registrations': avg_registrations,
        'outcome_rows': outcome_rows,
        'event_type_summary': event_type_summary,
        'community_summary': community_summary,
        'recent_requests': recent_requests,
        **get_sidebar_counts(request.user),
    }
    return render(request, 'dashboard/reports/projects.html', context)


# ====== NOTIFICATIONS & SETTINGS ======

@require_http_methods(['POST'])
@user_passes_test(staff_required, login_url='login')
def mark_all_notifications_read(request):
    """Mark the current dashboard notification feed as read for this admin user."""
    notification_state, _ = AdminNotificationState.objects.get_or_create(user=request.user)
    notification_state.last_read_at = timezone.now()
    notification_state.save(update_fields=['last_read_at', 'updated_at'])

    if is_ajax_request(request):
        return success_json_response(
            'All notifications marked as read.',
            extra_data={'unread_notifications_count': 0},
        )

    messages.success(request, 'All notifications marked as read.')
    return redirect('dashboard:notifications')


@user_passes_test(staff_required, login_url='login')
def notifications(request):
    """Notifications page"""
    context = get_dashboard_notifications(user=request.user, limit=18, dropdown_limit=6)
    return render(request, 'dashboard/notifications.html', context)


@user_passes_test(staff_required, login_url='login')
def settings_view(request):
    """Settings page — profile update, password change, and platform info."""
    from django.conf import settings as django_settings
    import django

    profile_form = AdminProfileForm(instance=request.user)
    password_form = AdminPasswordForm(user=request.user)
    active_section = 'account'

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            active_section = 'account'
            profile_form = AdminProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('dashboard:settings')

        elif action == 'change_password':
            active_section = 'security'
            password_form = AdminPasswordForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                request.user.set_password(password_form.cleaned_data['new_password'])
                request.user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully. You are still logged in.')
                return redirect('dashboard:settings')

    # Mask sensitive values before sending to template
    email_host = getattr(django_settings, 'EMAIL_HOST', '')
    email_user = getattr(django_settings, 'EMAIL_HOST_USER', '')
    email_port = getattr(django_settings, 'EMAIL_PORT', '')
    email_use_tls = getattr(django_settings, 'EMAIL_USE_TLS', False)
    default_from_email = getattr(django_settings, 'DEFAULT_FROM_EMAIL', '')

    def _mask(value):
        """Show only first 3 chars + asterisks — never expose full secrets."""
        s = str(value)
        return (s[:3] + '*' * max(len(s) - 3, 4)) if len(s) > 3 else '***'

    platform_info = {
        'django_version': django.get_version(),
        'time_zone': getattr(django_settings, 'TIME_ZONE', 'UTC'),
        'language_code': getattr(django_settings, 'LANGUAGE_CODE', 'en-us'),
        'debug_mode': getattr(django_settings, 'DEBUG', False),
        'database_engine': django_settings.DATABASES['default']['ENGINE'].split('.')[-1],
        'allowed_hosts': ', '.join(getattr(django_settings, 'ALLOWED_HOSTS', [])),
        'use_tz': getattr(django_settings, 'USE_TZ', True),
        'media_root': str(getattr(django_settings, 'MEDIA_ROOT', '')),
        'static_root': str(getattr(django_settings, 'STATIC_ROOT', '')),
    }

    email_info = {
        'host': email_host,
        'port': email_port,
        'use_tls': email_use_tls,
        'user': _mask(email_user) if email_user else '—',
        'default_from': default_from_email,
    }

    security_info = {
        'csrf_cookie_httponly': getattr(django_settings, 'CSRF_COOKIE_HTTPONLY', False),
        'session_cookie_httponly': getattr(django_settings, 'SESSION_COOKIE_HTTPONLY', False),
        'session_cookie_age_days': getattr(django_settings, 'SESSION_COOKIE_AGE', 1209600) // 86400,
        'https_redirect': getattr(django_settings, 'SECURE_SSL_REDIRECT', False),
        'hsts_enabled': bool(getattr(django_settings, 'SECURE_HSTS_SECONDS', 0)),
        'x_frame_options': getattr(django_settings, 'X_FRAME_OPTIONS', 'SAMEORIGIN'),
    }

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'active_section': active_section,
        'platform_info': platform_info,
        'email_info': email_info,
        'security_info': security_info,
        **get_sidebar_counts(request.user),
    }
    return render(request, 'dashboard/settings.html', context)
