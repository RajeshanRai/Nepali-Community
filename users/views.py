from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.views.generic import CreateView
from django.contrib import messages
from django.utils import timezone
from .models import CustomUser
from .forms import CustomAuthForm, RegistrationForm
from django.urls import reverse_lazy


class LoginView(AuthLoginView):
    template_name = 'users/login.html'
    form_class = CustomAuthForm

    def form_valid(self, form):
        from dashboard.models import MemberModerationAction

        remember_me = form.cleaned_data.get('remember_me')
        if remember_me:
            self.request.session.set_expiry(1209600)  # 2 weeks
        else:
            self.request.session.set_expiry(0)  # Expires on browser close

        latest_unseen_warning = MemberModerationAction.objects.filter(
            user=form.get_user(),
            action='warn',
            seen_at__isnull=True,
        ).order_by('-created_at').first()

        if latest_unseen_warning:
            self.request.session['login_warning_notice'] = {
                'message': latest_unseen_warning.reason.strip() or 'Please review your recent account warning.',
                'issued_at': latest_unseen_warning.created_at.strftime('%b %d, %Y %I:%M %p'),
            }
            latest_unseen_warning.seen_at = timezone.now()
            latest_unseen_warning.save(update_fields=['seen_at'])

        return super().form_valid(form)


class LogoutView(AuthLogoutView):
    next_page = reverse_lazy('home')


class RegisterView(CreateView):
    model = CustomUser
    form_class = RegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        name = self.object.first_name or self.object.username
        messages.success(
            self.request,
            f'Welcome to the Nepali Community of Vancouver, {name}! Your account has been created. Please log in.'
        )
        return response
