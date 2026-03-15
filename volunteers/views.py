from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.db import IntegrityError
from .models import VolunteerOpportunity, VolunteerApplication, VolunteerRequest
from .forms import VolunteerApplicationForm, VolunteerRequestForm


class VolunteerListView(ListView):
    model = VolunteerOpportunity
    template_name = 'volunteers/list.html'
    context_object_name = 'opportunities'
    
    def get_queryset(self):
        qs = VolunteerOpportunity.objects.filter(status='open')
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = VolunteerOpportunity.CATEGORY_CHOICES
        context['current_category'] = self.request.GET.get('category', '')
        initial_data = {}

        if self.request.user.is_authenticated:
            initial_data = {
                'name': self.request.user.get_full_name() or self.request.user.username,
                'email': self.request.user.email,
                'phone': getattr(self.request.user, 'phone_number', ''),
            }

        context['request_form'] = VolunteerRequestForm(initial=initial_data)
        return context


def volunteer_request_submit(request):
    if request.method != 'POST':
        return redirect('volunteer_list')

    form = VolunteerRequestForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, 'Volunteer request submitted successfully. Our team will contact you soon.')
    else:
        first_error = next(iter(form.errors.values()))[0] if form.errors else 'Please check your submission.'
        messages.error(request, first_error)

    return redirect('volunteer_list')


class VolunteerDetailView(DetailView):
    model = VolunteerOpportunity
    template_name = 'volunteers/detail.html'
    context_object_name = 'opportunity'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['application_form'] = VolunteerApplicationForm()
        
        # Pre-fill form if user is authenticated
        if self.request.user.is_authenticated:
            initial_data = {
                'name': self.request.user.get_full_name() or self.request.user.username,
                'email': self.request.user.email,
                'phone': getattr(self.request.user, 'phone_number', ''),
            }
            context['application_form'] = VolunteerApplicationForm(initial=initial_data)
        
        return context


class VolunteerApplyView(CreateView):
    model = VolunteerApplication
    form_class = VolunteerApplicationForm
    template_name = 'volunteers/apply.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        opportunity = get_object_or_404(VolunteerOpportunity, pk=self.kwargs['pk'])
        
        # Check if opportunity is still open
        if not opportunity.is_active:
            messages.error(self.request, 'This volunteer opportunity is no longer accepting applications.')
            return self.form_invalid(form)
        
        form.instance.opportunity = opportunity
        if self.request.user.is_authenticated:
            form.instance.applicant = self.request.user
            form.instance.name = self.request.user.get_full_name() or self.request.user.username
            form.instance.email = (self.request.user.email or '').strip()
            if not form.instance.phone:
                form.instance.phone = (getattr(self.request.user, 'phone_number', '') or '').strip()

        # Prevent duplicate application (same email for same opportunity)
        submitted_email = (form.cleaned_data.get('email') or '').strip()
        already_applied = VolunteerApplication.objects.filter(
            opportunity=opportunity,
            email__iexact=submitted_email,
        ).exists()
        if already_applied:
            form.add_error('email', 'You have already applied for this volunteer opportunity with this email.')
            messages.warning(self.request, 'You already submitted an application for this opportunity.')
            return self.form_invalid(form)
        
        try:
            response = super().form_valid(form)
        except IntegrityError:
            # Race-condition-safe fallback in case two requests submit simultaneously.
            form.add_error('email', 'You have already applied for this volunteer opportunity with this email.')
            messages.warning(self.request, 'You already submitted an application for this opportunity.')
            return self.form_invalid(form)

        messages.success(self.request, 'Your volunteer application has been submitted successfully! We will contact you soon.')
        return response
    
    def get_success_url(self):
        return reverse_lazy('volunteer_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['opportunity'] = get_object_or_404(VolunteerOpportunity, pk=self.kwargs['pk'])

        if self.request.user.is_authenticated:
            profile_phone = (getattr(self.request.user, 'phone_number', '') or '').strip()
            context['prefilled_name'] = self.request.user.get_full_name() or self.request.user.username
            context['prefilled_email'] = (self.request.user.email or '').strip()
            context['needs_phone'] = not bool(profile_phone)
        else:
            context['needs_phone'] = True

        return context
