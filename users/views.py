from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.views.generic import CreateView
from django.contrib import messages
from django.utils import timezone
from .models import CustomUser
from .forms import CustomAuthForm, RegistrationForm
from django.urls import reverse_lazy
from core.email_utils import send_notification_email, build_branded_email_html, build_security_alert_html


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

        if self.object.email:
            send_notification_email(
                subject='Welcome to Nepali Community of Vancouver',
                message=(
                    f"Hi {name},\n\n"
                    "Your account has been created successfully. "
                    "You can now log in and participate in events, announcements, and volunteer programs.\n\n"
                    "- Nepali Community of Vancouver"
                ),
                recipients=[self.object.email],
                html_message=build_branded_email_html(
                    title='Welcome to Our Community',
                    greeting=f'Hi {name},',
                    intro='Your account is now active and ready to use.',
                    paragraphs=[
                        'You can now discover cultural programs, community announcements, and volunteer opportunities across Vancouver.',
                        'We are excited to have you with us and look forward to your participation.',
                    ],
                    cta_text='Sign In to Your Account',
                    cta_url=self.request.build_absolute_uri(reverse_lazy('login')),
                ),
            )

        messages.success(
            self.request,
            f'Welcome to the Nepali Community of Vancouver, {name}! Your account has been created. Please log in.'
        )
        return response


class CustomPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.txt'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.user and self.user.email:
            send_notification_email(
                subject='Your password was reset',
                message=(
                    f"Hi {self.user.get_full_name() or self.user.username},\n\n"
                    "Your account password was reset successfully.\n"
                    "If this was not you, please contact support immediately.\n\n"
                    "- Nepali Community of Vancouver"
                ),
                recipients=[self.user.email],
                html_message=build_security_alert_html(
                    title='Password Updated Successfully',
                    greeting=f"Hi {self.user.get_full_name() or self.user.username},",
                    severity_label='Security Notice',
                    summary='Your account password was changed successfully.',
                    action_items=[
                        'If you made this change, no further action is required.',
                        'If this was unexpected, reset your password again and contact support immediately.',
                    ],
                    cta_text='Go to Login',
                    cta_url=self.request.build_absolute_uri(reverse_lazy('login')),
                ),
            )
        return response
