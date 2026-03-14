from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum, Q, Avg, Case, When, IntegerField
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.contrib import messages
from django.urls import reverse
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
from .forms import (
    ProgramForm, RequestEventForm, VolunteerOpportunityForm,
    AnnouncementForm, FAQForm, DonationForm, ContactMessageForm, CommunityForm
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
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)

    context = {
        'applications': applications,
        'volunteer_requests': volunteer_requests,
        'status_filter': status_filter,
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': applications.filter(status='pending').count() + volunteer_requests.filter(status='new').count(),
        'unread_notifications_count': 0,
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
@user_passes_test(staff_required, login_url='login')
def donations_list(request):
    """List all donations"""
    donations = Donation.objects.select_related('user').all().order_by('-created_at')
    search = request.GET.get('search', '')
    selected_status = request.GET.get('status', '').strip()

    if selected_status:
        donations = donations.filter(status=selected_status)

    if search:
        donations = donations.filter(
            Q(donor_name__icontains=search)
            | Q(donor_email__icontains=search)
            | Q(transaction_ref__icontains=search)
            | Q(purpose__icontains=search)
        )

    context = {
        'donations': donations,
        'search': search,
        'selected_status': selected_status,
        'status_choices': Donation.DONATION_STATUS,
    }
    return render(request, 'dashboard/donations/list.html', context)


@user_passes_test(staff_required, login_url='login')
def donation_create(request):
    """Create a donation record"""
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save()
            messages.success(request, f'Donation #{donation.pk} created successfully.')
            return redirect('dashboard:donations_list')
    else:
        form = DonationForm()
    return render(request, 'dashboard/donations/form.html', {'form': form, 'title': 'Create Donation'})


@user_passes_test(staff_required, login_url='login')
def donation_edit(request, pk):
    """Edit donation record"""
    donation = get_object_or_404(Donation, pk=pk)
    if request.method == 'POST':
        form = DonationForm(request.POST, instance=donation)
        if form.is_valid():
            form.save()
            messages.success(request, f'Donation #{donation.pk} updated successfully.')
            return redirect('dashboard:donations_list')
    else:
        form = DonationForm(instance=donation)
    return render(request, 'dashboard/donations/form.html', {'form': form, 'donation': donation, 'title': 'Edit Donation'})


@user_passes_test(staff_required, login_url='login')
def donation_delete(request, pk):
    """Delete donation record"""
    donation = get_object_or_404(Donation, pk=pk)
    if request.method == 'POST':
        donation_id = donation.pk
        donation.delete()
        messages.success(request, f'Donation #{donation_id} deleted successfully.')
        return redirect('dashboard:donations_list')
    return render(request, 'dashboard/donations/confirm_delete.html', {'donation': donation})


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
        form = ContactMessageForm()
    return render(request, 'dashboard/contacts/form.html', {'form': form, 'title': 'Create Contact Message'})


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
        form = ContactMessageForm(instance=message_obj)
    return render(request, 'dashboard/contacts/form.html', {'form': form, 'message_obj': message_obj, 'title': 'Edit Contact Message'})


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
    
    for i in range(6):
        month_date = timezone.now() - timedelta(days=30*i)
        month_name = month_date.strftime('%b %Y')
        project_months.insert(0, month_name)
        project_monthly_data.insert(0, Program.objects.filter(
            date__month=month_date.month,
            date__year=month_date.year
        ).count())
    
    def normalize_activity_datetime(value):
        if isinstance(value, datetime):
            dt_value = value
        elif isinstance(value, date):
            dt_value = datetime.combine(value, time.min)
        else:
            dt_value = timezone.now()

        if timezone.is_naive(dt_value):
            dt_value = timezone.make_aware(dt_value, timezone.get_current_timezone())

        return dt_value

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
                {'label': 'Manage', 'url': reverse('dashboard:admin_panel')},
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
        
        # Sidebar context
        'pending_projects_count': pending_projects,
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,  # Placeholder
    }
    
    return render(request, 'dashboard/admin_overview.html', context)


@user_passes_test(staff_required, login_url='login')
def admin_analytics(request):
    """Analytics page with detailed charts and statistics"""
    context = {
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
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
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
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
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/projects/all.html', context)


@user_passes_test(staff_required, login_url='login')
def projects_pending(request):
    """Pending projects listing"""
    projects = RequestEvent.objects.filter(status='pending').order_by('-submitted_at')
    context = {
        'projects': projects,
        'pending_projects_count': projects.count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/projects/pending.html', context)


@user_passes_test(staff_required, login_url='login')
def projects_approved(request):
    """Approved projects listing"""
    projects = Program.objects.all().order_by('-date')
    context = {
        'projects': projects,
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
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
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/volunteers/all.html', context)


@user_passes_test(staff_required, login_url='login')
def volunteers_applications(request):
    """All volunteer applications listing"""
    applications = VolunteerApplication.objects.all().order_by('-applied_at')
    volunteer_requests = VolunteerRequest.objects.all().order_by('-created_at')
    context = {
        'applications': applications,
        'volunteer_requests': volunteer_requests,
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': applications.filter(status='pending').count() + volunteer_requests.filter(status='new').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/volunteers/applications.html', context)


# ====== USER MANAGEMENT VIEWS ======

@user_passes_test(staff_required, login_url='login')
def users_all(request):
    """All users listing"""
    users = CustomUser.objects.all().order_by('-date_joined')
    context = {
        'users': users,
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/users/all.html', context)


@user_passes_test(staff_required, login_url='login')
def users_roles(request):
    """User roles and permissions management"""
    users = CustomUser.objects.all().order_by('-date_joined')
    context = {
        'users': users,
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/users/roles.html', context)


# ====== CATEGORIES MANAGEMENT ======

@user_passes_test(staff_required, login_url='login')
def categories_list(request):
    """Categories listing"""
    categories = Community.objects.all().order_by('name')
    context = {
        'categories': categories,
        'pending_projects_count': RequestEvent.objects.filter(status='pending').count(),
        'pending_applications_count': VolunteerApplication.objects.filter(status='pending').count(),
        'unread_notifications_count': 0,
    }
    return render(request, 'dashboard/categories/list.html', context)


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
        form = CommunityForm()

    return render(request, 'dashboard/categories/form.html', {
        'form': form,
        'title': 'Create Category',
    })


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
        form = CommunityForm(instance=category)

    return render(request, 'dashboard/categories/form.html', {
        'form': form,
        'category': category,
        'title': 'Edit Category',
    })


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
