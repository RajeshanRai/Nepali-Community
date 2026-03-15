from django.views.generic import ListView, DetailView, FormView
from django.views import View
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_GET
from django.urls import reverse_lazy
from django.db.models import Q
from django.shortcuts import render
from communities.models import Community
from core.email_utils import send_notification_email, build_event_newsletter_html
from .models import Program, EventRegistration, RequestEvent
from .forms import GuestRegistrationForm, UserRegistrationForm, RequestEventForm
from users.tracking import track_recent_view
import json
import re


NEPALI_OBSERVANCES = [
    {
        'title': 'Maghe Sankranti',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': '1 Magh',
        'period': 'Mid January',
        'details': 'Traditional harvest celebration with tarul, ghee, and chaku.'
    },
    {
        'title': 'Sonam Lhosar',
        'category': 'Cultural',
        'category_slug': 'cultural',
        'nepali_date': 'Magh (varies)',
        'period': 'January / February',
        'details': 'New year celebration of Tamang and Himalayan communities.'
    },
    {
        'title': 'Maha Shivaratri',
        'category': 'Religious',
        'category_slug': 'religious',
        'nepali_date': 'Falgun Krishna Chaturdashi',
        'period': 'February / March',
        'details': 'Major Hindu observance dedicated to Lord Shiva.'
    },
    {
        'title': 'Gyalpo Lhosar',
        'category': 'Cultural',
        'category_slug': 'cultural',
        'nepali_date': 'Falgun (varies)',
        'period': 'February / March',
        'details': 'Tibetan new year marked with community prayers and gatherings.'
    },
    {
        'title': 'Fagu Purnima (Holi)',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Falgun Purnima',
        'period': 'March',
        'details': 'Festival of colors celebrated across Nepal.'
    },
    {
        'title': 'Ghode Jatra',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Chaitra (varies)',
        'period': 'March / April',
        'details': 'Traditional horse festival celebrated in Kathmandu Valley.'
    },
    {
        'title': 'Nepali New Year',
        'category': 'Public Holiday',
        'category_slug': 'holiday',
        'nepali_date': '1 Baisakh',
        'period': 'Mid April',
        'details': 'Start of the Bikram Sambat year with family and community events.'
    },
    {
        'title': 'Bisket Jatra',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'End Chaitra / Start Baisakh',
        'period': 'April',
        'details': 'Bhaktapur chariot festival associated with new year celebrations.'
    },
    {
        'title': 'Buddha Jayanti',
        'category': 'Public Holiday',
        'category_slug': 'holiday',
        'nepali_date': 'Baisakh Purnima',
        'period': 'April / May',
        'details': 'Birth anniversary of Lord Buddha.'
    },
    {
        'title': 'Ubhauli Sakela',
        'category': 'Cultural',
        'category_slug': 'cultural',
        'nepali_date': 'Baisakh / Jestha (varies)',
        'period': 'May / June',
        'details': 'Kirat community festival with Sakela Sili dance.'
    },
    {
        'title': 'Rato Machhindranath Jatra',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Baisakh / Jestha (varies)',
        'period': 'May / June',
        'details': 'Historic chariot procession celebrated in Patan.'
    },
    {
        'title': 'Janai Purnima',
        'category': 'Religious',
        'category_slug': 'religious',
        'nepali_date': 'Shrawan Purnima',
        'period': 'August',
        'details': 'Sacred thread changing ritual and Raksha Bandhan observance.'
    },
    {
        'title': 'Gai Jatra',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Bhadra Pratipada',
        'period': 'August / September',
        'details': 'Festival remembering departed family members.'
    },
    {
        'title': 'Krishna Janmashtami',
        'category': 'Religious',
        'category_slug': 'religious',
        'nepali_date': 'Bhadra Krishna Ashtami',
        'period': 'August / September',
        'details': 'Celebration of Lord Krishna’s birth.'
    },
    {
        'title': 'Teej',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Bhadra Shukla Tritiya',
        'period': 'August / September',
        'details': 'Women’s festival with fasting, dancing, and temple worship.'
    },
    {
        'title': 'Indra Jatra',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Bhadra (varies)',
        'period': 'September',
        'details': 'Major Kathmandu valley festival featuring Kumari Jatra.'
    },
    {
        'title': 'Constitution Day (Nepal)',
        'category': 'Public Holiday',
        'category_slug': 'holiday',
        'nepali_date': '3 Ashwin',
        'period': 'September',
        'details': 'National day marking promulgation of the constitution.'
    },
    {
        'title': 'Ghatasthapana',
        'category': 'Religious',
        'category_slug': 'religious',
        'nepali_date': 'Ashwin Shukla Pratipada',
        'period': 'September / October',
        'details': 'Opening day of Dashain with jamara planting.'
    },
    {
        'title': 'Fulpati',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Dashain Day 7',
        'period': 'September / October',
        'details': 'Dashain procession and ceremonial observances.'
    },
    {
        'title': 'Maha Ashtami',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Dashain Day 8',
        'period': 'September / October',
        'details': 'Important Dashain worship day.'
    },
    {
        'title': 'Maha Navami',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Dashain Day 9',
        'period': 'September / October',
        'details': 'Dashain worship and preparation day.'
    },
    {
        'title': 'Bijaya Dashami',
        'category': 'Public Holiday',
        'category_slug': 'holiday',
        'nepali_date': 'Dashain Day 10',
        'period': 'October',
        'details': 'Main Dashain tika and jamara blessing day.'
    },
    {
        'title': 'Kojagrat Purnima',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Dashain Day 15',
        'period': 'October',
        'details': 'Final day of Dashain celebrated on full moon.'
    },
    {
        'title': 'Laxmi Puja',
        'category': 'Religious',
        'category_slug': 'religious',
        'nepali_date': 'Kartik Krishna Aunsi',
        'period': 'October / November',
        'details': 'Tihar day dedicated to Goddess Laxmi.'
    },
    {
        'title': 'Kukur Tihar',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Kartik Krishna Chaturdashi',
        'period': 'October / November',
        'details': 'Tihar day honoring dogs with garlands and tika.'
    },
    {
        'title': 'Gai Tihar',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Kartik Krishna Trayodashi',
        'period': 'October / November',
        'details': 'Tihar observance honoring cows.'
    },
    {
        'title': 'Mha Puja / Nepal Sambat New Year',
        'category': 'Cultural',
        'category_slug': 'cultural',
        'nepali_date': 'Kartik Shukla Pratipada',
        'period': 'October / November',
        'details': 'Newar self-worship ritual and Nepal Sambat new year.'
    },
    {
        'title': 'Bhai Tika',
        'category': 'Public Holiday',
        'category_slug': 'holiday',
        'nepali_date': 'Kartik Shukla Dwitiya',
        'period': 'October / November',
        'details': 'Final day of Tihar celebrating sibling bond.'
    },
    {
        'title': 'Chhath Parva',
        'category': 'Religious',
        'category_slug': 'religious',
        'nepali_date': 'Kartik Shukla Shashthi',
        'period': 'October / November',
        'details': 'Sun worship festival, especially in Terai communities.'
    },
    {
        'title': 'Udhauli Sakela',
        'category': 'Cultural',
        'category_slug': 'cultural',
        'nepali_date': 'Mangsir (varies)',
        'period': 'November / December',
        'details': 'Kirat community seasonal migration and thanksgiving festival.'
    },
    {
        'title': 'Yomari Punhi',
        'category': 'Festival',
        'category_slug': 'festival',
        'nepali_date': 'Thinla Purnima',
        'period': 'December',
        'details': 'Newar harvest celebration with yomari delicacies.'
    },
]


MONTH_SEQUENCE = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def extract_month_tags(period_text):
    if not period_text:
        return []
    matched_months = []
    for month in MONTH_SEQUENCE:
        if re.search(rf'\b{month}\b', period_text, flags=re.IGNORECASE):
            matched_months.append(month)
    return matched_months


def build_nepali_observances_context():
    enriched_observances = []
    month_set = set()

    for observance in NEPALI_OBSERVANCES:
        month_tags = extract_month_tags(observance.get('period', ''))
        month_set.update(month_tags)

        enriched_observances.append({
            **observance,
            'month_tags': month_tags,
            'month_tags_csv': ','.join(month_tags),
        })

    months_present = [month for month in MONTH_SEQUENCE if month in month_set]
    return enriched_observances, months_present


class ProgramListView(ListView):
    model = Program
    template_name = 'programs/list.html'
    context_object_name = 'programs'
    
    def get_queryset(self):
        qs = Program.objects.all().order_by('date')
        q = self.request.GET.get('q', '')
        t = self.request.GET.get('type', '')
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        # map filter types
        type_map = {
            'festivals': 'festival',
            'workshops': 'workshop',
            'meetings': 'meeting',
            'cultural': 'cultural',
            'other': 'other',
        }
        if t and t in type_map:
            qs = qs.filter(event_type=type_map[t])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user registrations to context
        if self.request.user.is_authenticated:
            user_registrations = EventRegistration.objects.filter(
                user=self.request.user
            ).values_list('program_id', flat=True)
            context['user_registrations'] = list(user_registrations)
            # Get actual program objects for My Registrations section
            context['user_registered_programs'] = Program.objects.filter(
                id__in=user_registrations
            ).order_by('date')
        else:
            context['user_registrations'] = []
            context['user_registered_programs'] = []
        # pass current filters
        context['current_type'] = self.request.GET.get('type', '')
        context['search_q'] = self.request.GET.get('q', '')
        context['request_form'] = RequestEventForm()
        context['communities'] = Community.objects.all().order_by('name')
        
        # Generate event calendar data
        events_by_date = {}
        for program in Program.objects.all():
            date_str = program.date.strftime('%Y-%m-%d')
            if date_str not in events_by_date:
                events_by_date[date_str] = {'count': 0, 'events': []}
            events_by_date[date_str]['count'] += 1
            events_by_date[date_str]['events'].append({
                'id': program.id,
                'title': program.title,
                'type': program.event_type
            })
        context['events_json'] = json.dumps(events_by_date)
        
        return context


class RequestEventCreateView(View):
    def post(self, request):
        form = RequestEventForm(request.POST)
        if form.is_valid():
            inst = form.save(commit=False)
            if request.user.is_authenticated:
                inst.requester = request.user
                # allow logged-in users to override name/email/phone via form
                if not inst.requester_name:
                    inst.requester_name = request.user.get_full_name() or request.user.username
                if not inst.requester_email:
                    inst.requester_email = request.user.email
                if not inst.requester_phone:
                    inst.requester_phone = getattr(request.user, 'phone_number', '')
            else:
                if not inst.requester_name or not inst.requester_email:
                    # still respond in JSON for consistency
                    return JsonResponse({'success': False, 'message': 'Name and email are required.'})
            inst.status = 'pending'
            inst.save()
            success = True
            message = 'Request submitted and sent to admin for review.'
        else:
            success = False
            message = '; '.join([
                f"{field}: {', '.join(errors)}"
                for field, errors in form.errors.items()
            ]) or 'Please fill required fields.'
        # always return JSON for POSTs; front-end expects it
        return JsonResponse({'success': success, 'message': message})


class ProgramDetailView(DetailView):
    model = Program
    template_name = 'programs/detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program = self.get_object()
        track_recent_view(
            self.request,
            content_type='program',
            object_id=program.pk,
            title=program.title,
            url=self.request.path,
        )
        
        # Check if user is registered
        if self.request.user.is_authenticated:
            is_registered = EventRegistration.objects.filter(
                user=self.request.user,
                program=program
            ).exists()
            context['is_registered'] = is_registered
        else:
            context['is_registered'] = False
            
        # Get registration form
        if self.request.user.is_authenticated:
            context['registration_form'] = UserRegistrationForm(user=self.request.user)
        else:
            context['registration_form'] = GuestRegistrationForm()
            
        return context


class RegisterForEventView(View):
    """Handle event registration for both logged-in and non-logged-in users"""
    
    def post(self, request, program_id):
        try:
            program = Program.objects.get(id=program_id)
            
            if request.user.is_authenticated:
                # Logged-in user registration
                registration, created = EventRegistration.objects.get_or_create(
                    user=request.user,
                    program=program
                )
                
                if created:
                    program.registered_count += 1
                    program.save()
                    message = f"Successfully registered for {program.title}!"
                    success = True

                    if request.user.email:
                        send_notification_email(
                            subject=f"Event registration confirmed: {program.title}",
                            message=(
                                f"Hi {request.user.get_full_name() or request.user.username},\n\n"
                                f"You are registered for: {program.title}\n"
                                f"Date: {program.date}\n"
                                f"Location: {program.location or 'TBA'}\n\n"
                                "Thank you for participating."
                            ),
                            recipients=[request.user.email],
                            html_message=build_event_newsletter_html(
                                title='Event Registration Confirmed',
                                greeting=f"Hi {request.user.get_full_name() or request.user.username},",
                                summary='Your seat has been reserved successfully.',
                                event_name=program.title,
                                event_date=program.date.strftime('%B %d, %Y'),
                                venue_text=program.location or 'Community venue details will be shared shortly.',
                                category_text=program.get_event_type_display() if hasattr(program, 'get_event_type_display') else (program.event_type or 'Community Event'),
                                detail_points=[
                                    'Please arrive 10-15 minutes early for smooth check-in.',
                                    'Bring any essentials relevant to this event type.',
                                ],
                            ),
                        )
                else:
                    message = "You are already registered for this event."
                    success = False
            else:
                # Guest registration
                form = GuestRegistrationForm(request.POST)
                if form.is_valid():
                    registration = form.save(commit=False)
                    registration.program = program
                    registration.save()
                    
                    program.registered_count += 1
                    program.save()
                    
                    message = f"Successfully registered for {program.title}!"
                    success = True

                    if registration.guest_email:
                        send_notification_email(
                            subject=f"Event registration confirmed: {program.title}",
                            message=(
                                f"Hi {registration.guest_name or 'Guest'},\n\n"
                                f"You are registered for: {program.title}\n"
                                f"Date: {program.date}\n"
                                f"Location: {program.location or 'TBA'}\n\n"
                                "Thank you for participating."
                            ),
                            recipients=[registration.guest_email],
                            html_message=build_event_newsletter_html(
                                title='Event Registration Confirmed',
                                greeting=f"Hi {registration.guest_name or 'Community Member'},",
                                summary='Your registration has been received and confirmed.',
                                event_name=program.title,
                                event_date=program.date.strftime('%B %d, %Y'),
                                venue_text=program.location or 'Community venue details will be shared shortly.',
                                category_text=program.get_event_type_display() if hasattr(program, 'get_event_type_display') else (program.event_type or 'Community Event'),
                                detail_points=[
                                    'Please keep this email for your reference.',
                                    'We look forward to welcoming you at the event.',
                                ],
                            ),
                        )
                else:
                    message = "Error: Please fill in all required fields."
                    success = False
                    
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': success, 'message': message})
            else:
                # Redirect back to referrer or programs page
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/programs/'))
                
        except Program.DoesNotExist:
            message = "Program not found."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': message}, status=404)
            else:
                return HttpResponseRedirect('/programs/')


class UnregisterForEventView(View):
    """Allow authenticated users to cancel a registration"""

    def post(self, request, program_id):
        if not request.user.is_authenticated:
            response = {'success': False, 'message': 'Login required to unregister.'}
            return JsonResponse(response, status=403)

        try:
            program = Program.objects.get(id=program_id)
            reg = EventRegistration.objects.filter(user=request.user, program=program).first()
            if reg:
                reg.delete()
                # decrement count but not below zero
                program.registered_count = max(0, program.registered_count - 1)
                program.save()
                message = f"You have been unregistered from {program.title}."
                success = True
            else:
                message = "You were not registered for this event."
                success = False

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': success, 'message': message})
            else:
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/programs/'))
        except Program.DoesNotExist:
            message = "Program not found."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': message}, status=404)
            else:
                return HttpResponseRedirect('/programs/')


class UserRegistrationsView(ListView):
    """View user's event registrations"""
    template_name = 'programs/my_registrations.html'
    context_object_name = 'registrations'
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return EventRegistration.objects.filter(
            user=self.request.user
        ).select_related('program').order_by('-registered_at')


class CalendarView(View):
    """Dedicated calendar view page"""
    def get(self, request):
        template_name = 'programs/calendar.html'
        nepali_observances, nepali_observance_months = build_nepali_observances_context()
        
        # Generate event calendar data
        events_by_date = {}
        for program in Program.objects.all():
            date_str = program.date.strftime('%Y-%m-%d')
            if date_str not in events_by_date:
                events_by_date[date_str] = {'count': 0, 'events': []}
            events_by_date[date_str]['count'] += 1
            events_by_date[date_str]['events'].append({
                'id': program.id,
                'title': program.title,
                'type': program.event_type
            })
        
        context = {
            'events_json': json.dumps(events_by_date),
            'nepali_observances': nepali_observances,
            'nepali_observance_months': nepali_observance_months,
        }
        return render(request, template_name, context)


@user_passes_test(lambda u: u.is_active and u.is_staff)
@require_GET
def programs_recent_requests(request):
    limit = int(request.GET.get('limit', 10))
    qs = RequestEvent.objects.order_by('-submitted_at')[:limit]
    data = []
    for r in qs:
        data.append({
            'id': r.id,
            'title': r.title,
            'requester_name': r.requester_name,
            'requester_email': r.requester_email,
            'submitted_at': r.submitted_at.isoformat(),
            'handled': r.handled,
        })
    return JsonResponse(data, safe=False)
