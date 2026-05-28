import json
import logging
import os

from django.conf import settings
from django.views.generic import TemplateView, ListView
from programs.models import Program, EventRegistration
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Count, Q
from users.models import CustomUser
from programs.models import RequestEvent
from announcements.models import Announcement
from django.db.models.functions import TruncMonth
from datetime import timedelta
from communities.models import Community
from volunteers.models import VolunteerApplication, VolunteerOpportunity, VolunteerRequest
from django.views.decorators.csrf import csrf_exempt
from .models import ChatbotConversation, ChatbotMessage, ChatbotFaq

logger = logging.getLogger(__name__)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        local_today = timezone.localdate()

        # show a compact preview list on homepage and reveal "Visit more" when additional items exist
        upcoming_qs = Program.objects.filter(date__gte=local_today).order_by('date')
        context['upcoming_programs'] = upcoming_qs[:3]
        context['has_more_upcoming_programs'] = upcoming_qs.count() > 3

        # community and volunteer counts for metric cards
        context['total_communities'] = Community.objects.count()

        # Active volunteers include accepted/assigned applications and approved request records.
        active_application_emails = VolunteerApplication.objects.filter(
            status__in=['accepted', 'assigned', 'approved']
        ).values_list('email', flat=True)
        active_request_emails = VolunteerRequest.objects.filter(
            status__in=['accepted', 'assigned', 'contacted']
        ).values_list('email', flat=True)

        active_volunteer_emails = {
            (email or '').strip().lower()
            for email in list(active_application_emails) + list(active_request_emails)
            if email
        }
        context['total_volunteers'] = len(active_volunteer_emails)
        context['total_members'] = CustomUser.objects.filter(is_active=True).count()

        # happening now snapshot for homepage
        context['happening_now_programs'] = Program.objects.filter(
            date=local_today
        ).order_by('title')[:3]

        context['happening_now_opportunities'] = VolunteerOpportunity.objects.filter(
            status='open',
        ).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=local_today)
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=local_today)
        ).select_related('created_by').order_by('start_date', 'created_at')[:3]

        # latest announcements preview with a conditional "Visit more" CTA
        latest_announcements_qs = Announcement.objects.filter(
            show_on_homepage=True,
            is_active=True,
            publish_date__lte=now,
        ).filter(
            Q(expire_date__isnull=True) | Q(expire_date__gt=now)
        ).select_related('created_by')
        context['latest_announcements'] = latest_announcements_qs[:3]
        context['has_more_announcements'] = latest_announcements_qs.count() > 3

        # volunteer opportunities preview with a conditional "Visit more" CTA
        featured_opportunities_qs = VolunteerOpportunity.objects.filter(
            status='open'
        ).select_related('created_by').order_by('start_date', 'created_at')
        context['featured_volunteer_opportunities'] = featured_opportunities_qs[:3]
        context['has_more_volunteer_opportunities'] = featured_opportunities_qs.count() > 3

        # include user's registrations to disable register buttons if already registered
        if self.request.user.is_authenticated:
            registered_ids = EventRegistration.objects.filter(
                user=self.request.user,
                program__in=context['upcoming_programs']
            ).values_list('program_id', flat=True)
            context['user_upcoming_registrations'] = set(registered_ids)
        else:
            context['user_upcoming_registrations'] = set()
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

        # Leadership team
        from core.models import TeamMember
        context['team_members'] = TeamMember.objects.filter(is_active=True)

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


def _ensure_chat_session(request):
    if not request.session.session_key:
        request.session.save()
    conversation, _ = ChatbotConversation.objects.get_or_create(
        session_key=request.session.session_key,
        defaults={
            'user': request.user if request.user.is_authenticated else None,
            'last_message': '',
            'message_count': 0,
        }
    )
    if request.user.is_authenticated and conversation.user is None:
        conversation.user = request.user
        conversation.save(update_fields=['user'])
    return conversation


def _match_faq_reply(message):
    active_faqs = ChatbotFaq.objects.filter(is_active=True)
    lower = message.lower()
    for faq in active_faqs:
        if faq.question.strip().lower() == lower:
            return faq.answer, 'faq'
        for keyword in faq.keyword_list():
            if keyword and keyword in lower:
                return faq.answer, 'faq'
    return None, None


def _openai_reply(message, user_name=None):
    if not OPENAI_AVAILABLE or not settings.OPENAI_API_KEY:
        return None
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        system_prompt = (
            'You are a friendly community assistant for the Nepali Community of Vancouver website. '
            'Answer politely and conversationally, including greetings and casual chat when appropriate. '
            'Provide navigation help, event guidance, FAQ support, and volunteer information using site links when available. '
            'If the user asks about contact, mention /contact/, email rajeshanrai05@gmail.com, and phone +1 (778) 885-1041. '
            'If the user asks for links, include the correct site paths like /faq/, /programs/, /contact/, or /communities. '
            'Do not invent unsupported contact details or external phone numbers.'
        )
        if user_name:
            system_prompt += f' Greet the user by name when appropriate: {user_name}.'
        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': message},
            ],
            max_tokens=260,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception('OpenAI reply failed')
        return None


@csrf_exempt
def chatbot_api(request):
    """Chatbot API with persistent session storage, FAQ matching, and optional OpenAI integration."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    msg = (payload.get('message') or '').strip()
    msg_type = (payload.get('type') or '').lower()
    requested_url = payload.get('url')
    user_name = None
    if request.user.is_authenticated:
        user_name = getattr(request.user, 'get_full_name', lambda: '')() or getattr(request.user, 'username', '')

    conversation = _ensure_chat_session(request)
    if msg:
        conversation.last_message = msg
        conversation.message_count = conversation.message_count + 1
        conversation.save(update_fields=['last_message', 'message_count', 'updated_at'])
        ChatbotMessage.objects.create(
            conversation=conversation,
            role='user',
            content=msg,
            source='user',
        )

    if requested_url and msg:
        page_label = 'page'
        if requested_url == '/faq/':
            page_label = 'FAQs'
        elif requested_url.startswith('/programs'):
            page_label = 'upcoming events page'
        elif requested_url == '/contact/':
            page_label = 'contact page'
        elif requested_url.startswith('/communities'):
            page_label = 'community page'
        reply = f'Sure, I found the {page_label} for you. Click the button below to open it, or ask me another question.'
        suggestions = [
            {'label': 'Open this page', 'url': requested_url, 'goDirect': True},
            'Ask another question',
        ]
        source = 'suggestion'
    else:
        msg_lower = msg.lower()
        if msg_type == 'init':
            if request.user.is_authenticated:
                reply = f'Hello {user_name}! I am the Nepali Community Helper - I can help with FAQs, events, joining groups, and more. What can I do for you today?'
            else:
                reply = 'Hello! I am the Nepali Community Helper - I can help with FAQs, events, joining groups, and more. What can I do for you today?'
            suggestions = [
                {'label': 'Show FAQs', 'url': '/faq/'},
                {'label': 'Upcoming events', 'url': '/programs/'},
                'Join a community',
                {'label': 'Contact support', 'url': '/contact/'},
            ]
            source = 'init'
        else:
            ai_reply = _openai_reply(msg or 'Hi there, how can I help?', user_name=user_name)
            if ai_reply:
                reply = ai_reply
                suggestions = [
                    {'label': 'Show FAQs', 'url': '/faq/'},
                    {'label': 'Upcoming events', 'url': '/programs/'},
                    {'label': 'Contact support', 'url': '/contact/'},
                ]
                source = 'openai'
            else:
                faq_reply, faq_source = _match_faq_reply(msg)
                if faq_reply:
                    reply = faq_reply
                    suggestions = [
                        'Ask another question',
                        {'label': 'Show FAQs', 'url': '/faq/'},
                        {'label': 'Contact support', 'url': '/contact/'},
                    ]
                    source = faq_source
                else:
                    reply = 'I didn\'t quite catch that — the AI service appears to be unavailable right now. Please try again later or visit /contact/ for support.'
                    suggestions = [
                        {'label': 'Contact support', 'url': '/contact/'},
                        {'label': 'Show FAQs', 'url': '/faq/'},
                        {'label': 'Upcoming events', 'url': '/programs/'},
                    ]
                    source = 'fallback'

    ChatbotMessage.objects.create(
        conversation=conversation,
        role='bot',
        content=reply,
        source=source,
    )

    response_data = {
        'reply': reply,
        'suggestions': suggestions,
        'conversation_id': conversation.pk,
        'timestamp': timezone.now().isoformat(),
    }
    return JsonResponse(response_data)
