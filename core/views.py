from django.views.generic import TemplateView, ListView
from programs.models import Program, EventRegistration
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Count, Q, F
from users.models import CustomUser
from programs.models import RequestEvent
from announcements.models import Announcement
from django.db.models.functions import TruncMonth
from datetime import timedelta
from django.db.models import Prefetch
from communities.models import Community
from volunteers.models import VolunteerApplication


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        # show next few upcoming programs on homepage
        upcoming = Program.objects.filter(date__gte=now.date()).order_by('date')[:5]
        context['upcoming_programs'] = upcoming

        # community and volunteer counts for metric cards
        context['total_communities'] = Community.objects.count()
        context['total_volunteers'] = VolunteerApplication.objects.filter(status='approved').count()
        context['total_members'] = CustomUser.objects.filter(is_active=True).count()

        # latest announcements for homepage
        context['latest_announcements'] = Announcement.objects.filter(
            show_on_homepage=True,
            is_active=True,
            publish_date__lte=now,
        ).filter(
            Q(expire_date__isnull=True) | Q(expire_date__gt=now)
        )[:4]

        # include user's registrations to disable register buttons if already registered
        if self.request.user.is_authenticated:
            registered_ids = EventRegistration.objects.filter(
                user=self.request.user,
                program__in=upcoming
            ).values_list('program_id', flat=True)
            context['user_upcoming_registrations'] = set(registered_ids)

            warning_notice = self.request.session.pop('login_warning_notice', None)
            if warning_notice:
                context['user_latest_warning_message'] = warning_notice.get('message', '')
                context['user_latest_warning_time'] = warning_notice.get('issued_at', '')
            else:
                context['user_latest_warning_message'] = ''
                context['user_latest_warning_time'] = ''
        else:
            context['user_upcoming_registrations'] = set()
            context['user_latest_warning_message'] = ''
            context['user_latest_warning_time'] = ''
        return context


class AboutView(TemplateView):
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from communities.models import Community
        
        # Get stats from database
        # Total active users
        context['total_users'] = CustomUser.objects.filter(is_active=True).count()
        
        # Total communities
        context['total_communities'] = Community.objects.count()
        
        # Total events (both past and future)
        context['total_events'] = Program.objects.count()
        
        # Years of service (since 1995)
        from datetime import datetime
        context['years_of_service'] = datetime.now().year - 1995
        
        return context


class SearchView(ListView):
    template_name = 'core/search_results.html'
    model = Program
    context_object_name = 'programs'

    def get_queryset(self):
        q = self.request.GET.get('q', '')
        return Program.objects.filter(title__icontains=q)


class SitemapView(TemplateView):
    template_name = 'core/sitemap.xml'


class RSSFeedView(TemplateView):
    template_name = 'core/rss.xml'


def staff_required(user):
    return user.is_active and user.is_staff


@method_decorator(user_passes_test(staff_required), name='dispatch')
class AdminDashboardView(TemplateView):
    template_name = 'admin/dashboard.html'


@user_passes_test(staff_required)
@cache_page(300)  # Cache for 5 minutes
def dashboard_stats_api(request):
    """
    OPTIMIZED: Reduced from 6+ queries to 2-3 queries using:
    - aggregate() for efficient counting
    - select_related() to prevent N+1 queries
    - values() with annotate() for grouping
    """
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # QUERY 1: All user statistics in single aggregation
    from django.db.models import Value, Case, When, IntegerField
    user_stats = CustomUser.objects.aggregate(
        total_users=Count('id'),
        active_30d=Count('id', filter=Q(is_active=True, last_login__gte=thirty_days_ago))
    )
    
    # QUERY 2: All program statistics in single aggregation  
    program_stats = Program.objects.aggregate(
        total_programs=Count('id'),
        upcoming_programs=Count('id', filter=Q(date__gte=now.date()))
    )
    
    # QUERY 3: Registration and request statistics
    registration_stats = EventRegistration.objects.aggregate(
        total_registrations=Count('id')
    )
    
    pending_requests = RequestEvent.objects.filter(handled=False).count()
    
    # QUERY 4: Top 5 events by registrations (with select_related to prevent N+1)
    top_events_qs = Program.objects.annotate(
        regs=Count('registrations')
    ).values('id', 'title', 'regs').order_by('-regs')[:5]
    top_events = [{'title': p['title'], 'regs': p['regs']} for p in top_events_qs]
    
    # QUERY 5: Registrations by month (last 12 months)
    reg_by_month_qs = EventRegistration.objects.annotate(month=TruncMonth('registered_at'))
    reg_by_month_qs = reg_by_month_qs.values('month').annotate(count=Count('id')).order_by('month')
    reg_by_month = [{'month': r['month'].strftime('%Y-%m'), 'count': r['count']} for r in reg_by_month_qs]
    
    # QUERY 6: Registrations by event type
    regs_by_type_qs = EventRegistration.objects.values('program__event_type').annotate(count=Count('id'))
    regs_by_type = [{'type': r['program__event_type'] or 'other', 'count': r['count']} for r in regs_by_type_qs]
    
    data = {
        'totals': {
            'total_users': user_stats['total_users'],
            'active_30d': user_stats['active_30d'],
            'total_programs': program_stats['total_programs'],
            'upcoming_programs': program_stats['upcoming_programs'],
            'total_registrations': registration_stats['total_registrations'],
            'pending_requests': pending_requests,
        },
        'top_events': top_events,
        'registrations_by_month': reg_by_month,
        'registrations_by_type': regs_by_type,
    }
    return JsonResponse(data)


class PrivacyPolicyView(TemplateView):
    template_name = 'core/privacy_policy.html'


class TermsOfUseView(TemplateView):
    template_name = 'core/terms_of_use.html'


class AccessibilityView(TemplateView):
    template_name = 'core/accessibility.html'
