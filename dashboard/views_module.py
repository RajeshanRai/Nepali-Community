from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum, Q, Avg, Case, When, IntegerField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from datetime import timedelta, datetime, date, time
import json

from users.models import CustomUser
from programs.models import Program, EventRegistration, RequestEvent
from donations.models import Donation
from communities.models import Community
from contacts.models import ContactMessage
from volunteers.models import VolunteerApplication, VolunteerOpportunity, VolunteerRequest
from announcements.models import Announcement
from dashboard.models import MemberModerationAction
from faqs.models import FAQ, FAQCategory
from .forms import (
    ProgramForm, RequestEventForm, VolunteerOpportunityForm,
    AnnouncementForm, FAQForm, DonationForm, ContactMessageForm, CommunityForm
)
from .utils import (
    normalize_activity_datetime,
    get_month_date_range,
    get_months_ago,
    get_sidebar_counts,
    is_ajax_request,
)


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


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin for class‑based views that restricts access to active staff/superusers.
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
    return render(request, 'dashboard/legacy/admin.html', context)


# ====== EVENT MANAGEMENT ======
@user_passes_test(staff_required, login_url='login')
def event_list(request):
    """List all events"""
    events = Program.objects.all().order_by('-date')
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
            form.save()
            messages.success(request, f'Event "{event.title}" has been updated successfully.')
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
    volunteer_requests = VolunteerRequest.objects.all().order_by('-created_at')
    available_opportunities = VolunteerOpportunity.objects.filter(status='open').order_by('title')
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
    """Approve volunteer application"""
    application = get_object_or_404(VolunteerApplication, pk=pk)
    application.status = 'approved'
    application.save()
    
    # Update volunteer opportunity positions
    opportunity = application.opportunity
    opportunity.positions_filled = VolunteerApplication.objects.filter(
        opportunity=opportunity, status='approved'
    ).count()
    
    if opportunity.positions_filled >= opportunity.positions_needed:
        opportunity.status = 'filled'
    
    opportunity.save()
    
    return JsonResponse({'success': True, 'message': 'Application approved'})


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

    approved_count = VolunteerApplication.objects.filter(
        opportunity=opportunity,
        status='approved'
    ).count()
    opportunity.positions_filled = approved_count

    if approved_count < opportunity.positions_needed and opportunity.status == 'filled':
        opportunity.status = 'open'

    opportunity.save(update_fields=['positions_filled', 'status'])
    return JsonResponse({'success': True, 'message': 'Application deleted'})


@user_passes_test(staff_required, login_url='login')
@require_http_methods(["POST"])
def volunteer_request_approve(request, pk):
    """Approve volunteer request by marking it contacted"""
    volunteer_request = get_object_or_404(VolunteerRequest, pk=pk)
    volunteer_request.status = 'contacted'
    volunteer_request.reviewed_at = timezone.now()
    volunteer_request.save(update_fields=['status', 'reviewed_at'])
    return JsonResponse({'success': True, 'message': 'Volunteer request approved'})


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
    opportunity_id = request.POST.get('opportunity_id')

    if not opportunity_id:
        return JsonResponse({'success': False, 'message': 'Opportunity is required.'}, status=400)

    opportunity = get_object_or_404(VolunteerOpportunity, pk=opportunity_id)

    approved_count = VolunteerApplication.objects.filter(
        opportunity=opportunity,
        status='approved'
    ).count()
    if opportunity.status != 'open' or approved_count >= opportunity.positions_needed:
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
            'status': 'approved',
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
        application.status = 'approved'
        application.reviewed_at = timezone.now()
        application.reviewed_by = request.user
        application.admin_notes = f'Assigned from volunteer request #{volunteer_request.id}'
        application.save()

    volunteer_request.status = 'contacted'
    volunteer_request.reviewed_at = timezone.now()
    volunteer_request.admin_notes = (
        f'Assigned to opportunity "{opportunity.title}" (ID: {opportunity.id}) by {request.user.username}'
    )
    volunteer_request.save(update_fields=['status', 'reviewed_at', 'admin_notes'])

    opportunity.positions_filled = VolunteerApplication.objects.filter(
        opportunity=opportunity,
        status='approved'
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
    status_filter = request.GET.get('status', '')
    if status_filter:
        requests = requests.filter(status=status_filter)
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
        
        # Get rejection reason from request body if provided
        try:
            data = json.loads(request.body)
            rejection_reason = data.get('reason', '')
        except json.JSONDecodeError:
            rejection_reason = ''
        
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
            form.save()
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
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
        search = self.request.GET.get('search', '')
        selected_status = self.request.GET.get('status', '').strip()
        if selected_status:
            qs = qs.filter(status=selected_status)
        if search:
            qs = qs.filter(
                Q(donor_name__icontains=search)
                | Q(donor_email__icontains=search)
                | Q(transaction_ref__icontains=search)
                | Q(purpose__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search': self.request.GET.get('search', ''),
            'selected_status': self.request.GET.get('status', ''),
            'status_choices': Donation.DONATION_STATUS,
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
    context = {
        # sidebar counts injected via context processor
    }
    return render(request, 'dashboard/admin_analytics.html', context)


@user_passes_test(staff_required, login_url='login')
def admin_activity(request):
    """Recent activity page showing all system activities"""
    # Get recent events, applications, requests
    recent_events = Program.objects.all().order_by('-date')[:20]
    recent_applications = VolunteerApplication.objects.all().order_by('-applied_at')[:20]
    recent_requests = RequestEvent.objects.all().order_by('-submitted_at')[:20]
    
    # Combine and sort by date
    activities = []
    
    for event in recent_events:
        activities.append({
            'type': 'event',
            'title': f'Event created: {event.title}',
            'date': event.date,
            'user': 'System',
            'has_time': False,
        })
    
    for app in recent_applications:
        activities.append({
            'type': 'application',
            'title': f'Volunteer application: {app.opportunity.title}',
            'date': app.applied_at,
            'user': app.applicant.username if app.applicant else app.name,
            'has_time': True,
        })
    
    for req in recent_requests:
        activities.append({
            'type': 'request',
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
    activities = activities[:50]
    
    context = {
        'activities': activities,
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
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/projects/rejected.html', context)


# ====== VOLUNTEER MANAGEMENT VIEWS ======

@user_passes_test(staff_required, login_url='login')
def volunteers_all(request):
    """All volunteer opportunities listing"""
    opportunities = VolunteerOpportunity.objects.all().order_by('-created_at')
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

    MemberModerationAction.objects.create(
        user=target_user,
        action='warn',
        reason=reason,
        created_by=request.user,
    )

    return JsonResponse({'success': True, 'message': 'Warning recorded successfully.'})


@user_passes_test(staff_required, login_url='login')
def users_roles(request):
    """User roles and permissions management"""
    users = CustomUser.objects.all().order_by('-date_joined')
    context = {
        'users': users,
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
    context = {
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/reports/monthly.html', context)


@user_passes_test(staff_required, login_url='login')
def reports_volunteers(request):
    """Volunteer activity report"""
    context = {
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/reports/volunteers.html', context)


@user_passes_test(staff_required, login_url='login')
def reports_projects(request):
    """Project success rate report"""
    context = {
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/reports/projects.html', context)


# ====== NOTIFICATIONS & SETTINGS ======

@user_passes_test(staff_required, login_url='login')
def notifications(request):
    """Notifications page"""
    context = {
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/notifications.html', context)


@user_passes_test(staff_required, login_url='login')
def settings_view(request):
    """Settings page"""
    context = {
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/settings.html', context)
