from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.auth import update_session_auth_hash, logout, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from django.contrib import messages
from django.utils import timezone
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.db.models import Q
from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse, NoReverseMatch
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
import base64
import io
import pyotp
import qrcode  # pyright: ignore[reportMissingImports]
from .models import CustomUser, LoginActivity, TwoFactorEmailCode
from .forms import (
    CustomAuthForm,
    RegistrationForm,
    ProfileUpdateForm,
    ProfilePasswordChangeForm,
    DeactivateAccountForm,
    TwoFactorCodeForm,
    AppTwoFactorSetupForm,
)
from core.email_utils import send_notification_email, build_branded_email_html, build_security_alert_html
from programs.models import EventRegistration, RequestEvent
from volunteers.models import VolunteerApplication, VolunteerRequest
from donations.models import Donation


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _send_verification_email(request, user):
    if not user.email:
        return False

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_path = reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    verify_url = request.build_absolute_uri(verify_path)

    return send_notification_email(
        subject='Verify your email address',
        message=(
            f"Hi {user.display_name},\n\n"
            "Please verify your email address to secure your account and enable full profile features.\n"
            f"Verification link: {verify_url}\n\n"
            "If you did not create this account, you can ignore this email."
        ),
        recipients=[user.email],
        html_message=build_security_alert_html(
            title='Verify Your Email Address',
            greeting=f'Hi {user.display_name},',
            severity_label='Account Verification',
            summary='Please confirm your email address to complete account security setup.',
            action_items=[
                'Click the verification button below.',
                'This helps protect your account and enables secure notifications.',
            ],
            cta_text='Verify Email',
            cta_url=verify_url,
        ),
    )


def _send_login_email_otp(user):
    if not user.email:
        return False

    otp = TwoFactorEmailCode.create_for_user(user)
    return send_notification_email(
        subject='Your login verification code',
        message=(
            f"Hi {user.display_name},\n\n"
            f"Your one-time login code is: {otp.code}\n"
            "This code expires in 10 minutes.\n\n"
            "If you did not try to sign in, reset your password immediately."
        ),
        recipients=[user.email],
        html_message=build_security_alert_html(
            title='Login Verification Code',
            greeting=f'Hi {user.display_name},',
            severity_label='Two-Factor Authentication',
            summary=f'Use this one-time code to complete your sign-in: {otp.code}',
            action_items=[
                'Enter the 6-digit code on the verification page.',
                'The code expires in 10 minutes.',
            ],
        ),
    )


def _build_totp_qr_data_uri(totp_uri):
    if not totp_uri:
        return None

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(totp_uri)
    qr.make(fit=True)

    image = qr.make_image(fill_color='black', back_color='white')
    with io.BytesIO() as output:
        image.save(output, format='PNG')
        encoded = base64.b64encode(output.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def _resolve_active_2fa_method(user):
    if not user.two_factor_enabled:
        return ''

    method = (user.two_factor_method or '').strip().lower()
    if method == CustomUser.TWO_FACTOR_METHOD_EMAIL:
        return method if bool(user.email) and user.email_verified else ''
    if method == CustomUser.TWO_FACTOR_METHOD_APP:
        return method if bool(user.two_factor_secret) else ''

    # Legacy fallback: treat existing secret as authenticator app setup.
    if user.two_factor_secret:
        return CustomUser.TWO_FACTOR_METHOD_APP
    return ''


def _get_authenticated_profile_url(request):
    if request.user.is_authenticated and request.user.is_superuser:
        try:
            return reverse('dashboard:profiles')
        except NoReverseMatch:
            pass
    return reverse('profile')


def _apply_login_side_effects(request, user, remember_me=False):
    from dashboard.models import MemberModerationAction

    if remember_me:
        request.session.set_expiry(1209600)
    else:
        request.session.set_expiry(0)

    latest_unseen_warning = MemberModerationAction.objects.filter(
        user=user,
        action='warn',
        seen_at__isnull=True,
    ).order_by('-created_at').first()

    if latest_unseen_warning:
        request.session['login_warning_notice'] = {
            'message': latest_unseen_warning.reason.strip() or 'Please review your recent account warning.',
            'issued_at': latest_unseen_warning.created_at.strftime('%b %d, %Y %I:%M %p'),
        }
        latest_unseen_warning.seen_at = timezone.now()
        latest_unseen_warning.save(update_fields=['seen_at'])

    LoginActivity.objects.create(
        user=user,
        ip_address=_get_client_ip(request),
        user_agent=(request.META.get('HTTP_USER_AGENT', '') or '')[:512],
    )


class LoginView(AuthLoginView):
    template_name = 'users/login.html'
    form_class = CustomAuthForm

    def form_valid(self, form):
        user = form.get_user()
        remember_me = form.cleaned_data.get('remember_me')
        active_2fa_method = _resolve_active_2fa_method(user)

        if active_2fa_method:
            self.request.session['pending_2fa_user_id'] = user.pk
            self.request.session['pending_2fa_backend'] = getattr(user, 'backend', 'django.contrib.auth.backends.ModelBackend')
            self.request.session['pending_2fa_remember_me'] = bool(remember_me)
            self.request.session['pending_2fa_next'] = self.get_success_url()
            self.request.session['pending_2fa_method'] = active_2fa_method

            if active_2fa_method == CustomUser.TWO_FACTOR_METHOD_EMAIL:
                sent = _send_login_email_otp(user)
                if not sent:
                    messages.error(self.request, 'We could not send your email verification code. Please try again.')
                    return redirect('login')
                messages.info(self.request, 'A 6-digit verification code has been sent to your email.')
            else:
                messages.info(self.request, 'Enter the code from your authenticator app to continue.')

            return redirect('two_factor_verify')

        _apply_login_side_effects(self.request, user, remember_me=remember_me)

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
        _send_verification_email(self.request, self.object)
        messages.info(self.request, 'We sent a verification email to your address. Please verify it to secure your account.')
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'
    profile_route_name = 'profile'

    def profile_redirect(self):
        return redirect(self.profile_route_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        volunteer_request_filters = Q(pk__in=[])

        if user.email:
            volunteer_request_filters |= Q(email__iexact=user.email)
        if user.phone_number:
            volunteer_request_filters |= Q(phone__iexact=user.phone_number)

        event_registrations = EventRegistration.objects.filter(user=user).select_related('program').order_by('-registered_at')[:6]
        event_requests = RequestEvent.objects.filter(requester=user).select_related('community', 'created_program').order_by('-submitted_at')[:6]
        volunteer_applications = VolunteerApplication.objects.filter(applicant=user).select_related('opportunity').order_by('-applied_at')[:6]
        volunteer_requests = VolunteerRequest.objects.filter(volunteer_request_filters).order_by('-created_at')[:6]
        donations = Donation.objects.filter(user=user).order_by('-created_at')[:6]
        login_activity = user.login_activities.all()[:8]
        recent_views = user.recently_viewed_content.all()[:10]

        profile_form = kwargs.get('profile_form') or ProfileUpdateForm(instance=user)
        password_form = kwargs.get('password_form') or ProfilePasswordChangeForm(user=user)
        deactivate_form = kwargs.get('deactivate_form') or DeactivateAccountForm(user=user)
        app_2fa_form = kwargs.get('app_2fa_form') or AppTwoFactorSetupForm()
        pending_totp_secret = self.request.session.get('pending_totp_secret')

        totp_setup_uri = None
        totp_qr_data_uri = None
        if pending_totp_secret:
            issuer = 'Nepali Community of Vancouver'
            account_name = user.email or user.username
            totp_setup_uri = pyotp.TOTP(pending_totp_secret).provisioning_uri(name=account_name, issuer_name=issuer)
            totp_qr_data_uri = _build_totp_qr_data_uri(totp_setup_uri)

        location_parts = [part for part in [user.location, user.country] if part]

        context.update({
            'profile_form': profile_form,
            'password_form': password_form,
            'deactivate_form': deactivate_form,
            'event_registrations': event_registrations,
            'event_requests': event_requests,
            'volunteer_applications': volunteer_applications,
            'volunteer_requests': volunteer_requests,
            'donations': donations,
            'login_activity': login_activity,
            'recent_views': recent_views,
            'profile_completion': self._get_profile_completion(user),
            'display_location': ', '.join(location_parts),
            'app_2fa_form': app_2fa_form,
            'pending_totp_secret': pending_totp_secret,
            'totp_setup_uri': totp_setup_uri,
            'totp_qr_data_uri': totp_qr_data_uri,
            'profile_action_url': reverse(self.profile_route_name),
        })
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'update_profile':
            profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                previous_email = request.user.email
                user = profile_form.save()
                messages.success(request, 'Your profile has been updated successfully.')
                if previous_email != user.email:
                    _send_verification_email(request, user)
                    if user.two_factor_method == CustomUser.TWO_FACTOR_METHOD_EMAIL:
                        user.two_factor_method = CustomUser.TWO_FACTOR_METHOD_NONE
                        user.two_factor_enabled = False
                        user.two_factor_enabled_at = None
                        user.save(update_fields=['two_factor_method', 'two_factor_enabled', 'two_factor_enabled_at'])
                        messages.warning(request, 'Email-based 2FA was disabled because your primary email changed.')
                    messages.info(request, 'Your email was changed. Verification status has been reset until you confirm the new address.')
                return self.profile_redirect()
            return self.render_to_response(self.get_context_data(profile_form=profile_form))

        if action == 'resend_verification_email':
            if request.user.email_verified:
                messages.info(request, 'Your email is already verified.')
                return self.profile_redirect()
            if not request.user.email:
                messages.error(request, 'Add an email address before requesting verification.')
                return self.profile_redirect()
            sent = _send_verification_email(request, request.user)
            if sent:
                messages.success(request, 'A new verification email was sent.')
            else:
                messages.error(request, 'Unable to send verification email right now. Please try again later.')
            return self.profile_redirect()

        if action == 'change_password':
            password_form = ProfilePasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been changed successfully.')
                return self.profile_redirect()
            return self.render_to_response(self.get_context_data(password_form=password_form))

        if action == 'deactivate_account':
            deactivate_form = DeactivateAccountForm(request.user, request.POST)
            if deactivate_form.is_valid():
                request.user.is_active = False
                request.user.save(update_fields=['is_active'])
                logout(request)
                messages.success(request, 'Your account has been deactivated.')
                return redirect('home')
            return self.render_to_response(self.get_context_data(deactivate_form=deactivate_form))

        if action == 'enable_email_2fa':
            if not request.user.email:
                messages.error(request, 'Add an email address before enabling email-based 2FA.')
                return self.profile_redirect()
            if not request.user.email_verified:
                messages.error(request, 'Verify your email first before enabling email-based 2FA.')
                return self.profile_redirect()
            request.user.two_factor_method = CustomUser.TWO_FACTOR_METHOD_EMAIL
            request.user.two_factor_secret = ''
            request.user.two_factor_enabled = True
            request.user.two_factor_enabled_at = timezone.now()
            request.user.save(update_fields=['two_factor_method', 'two_factor_secret', 'two_factor_enabled', 'two_factor_enabled_at'])
            request.session.pop('pending_totp_secret', None)
            messages.success(request, 'Email-based two-factor authentication is now enabled.')
            return self.profile_redirect()

        if action == 'start_app_2fa_setup':
            request.session['pending_totp_secret'] = pyotp.random_base32()
            messages.info(request, 'Scan the secret with your authenticator app and enter a code to confirm setup.')
            return self.profile_redirect()

        if action == 'confirm_app_2fa_setup':
            app_2fa_form = AppTwoFactorSetupForm(request.POST)
            secret = request.session.get('pending_totp_secret')
            if not secret:
                messages.error(request, 'Start authenticator setup first.')
                return self.profile_redirect()

            if app_2fa_form.is_valid():
                otp = app_2fa_form.cleaned_data['code']
                if pyotp.TOTP(secret).verify(otp, valid_window=1):
                    request.user.two_factor_secret = secret
                    request.user.two_factor_method = CustomUser.TWO_FACTOR_METHOD_APP
                    request.user.two_factor_enabled = True
                    request.user.two_factor_enabled_at = timezone.now()
                    request.user.save(update_fields=['two_factor_secret', 'two_factor_method', 'two_factor_enabled', 'two_factor_enabled_at'])
                    request.session.pop('pending_totp_secret', None)
                    messages.success(request, 'Authenticator app two-factor authentication is now enabled.')
                    return self.profile_redirect()
                app_2fa_form.add_error('code', 'Invalid authenticator code. Please try again.')
            return self.render_to_response(self.get_context_data(app_2fa_form=app_2fa_form))

        if action == 'disable_2fa':
            request.user.two_factor_method = CustomUser.TWO_FACTOR_METHOD_NONE
            request.user.two_factor_secret = ''
            request.user.two_factor_enabled = False
            request.user.two_factor_enabled_at = None
            request.user.save(update_fields=['two_factor_method', 'two_factor_secret', 'two_factor_enabled', 'two_factor_enabled_at'])
            request.session.pop('pending_totp_secret', None)
            messages.success(request, 'Two-factor authentication has been disabled for your account.')
            return self.profile_redirect()

        messages.error(request, 'We could not process that profile action.')
        return self.profile_redirect()

    def _get_profile_completion(self, user):
        fields = [
            bool(user.first_name),
            bool(user.last_name),
            bool(user.email),
            bool(user.phone_number),
            bool(user.birth_date),
            bool(user.location),
            bool(user.country),
            bool(user.bio),
            bool(user.profile_picture),
            bool(user.recovery_email),
        ]
        completed = sum(1 for item in fields if item)
        return round((completed / len(fields)) * 100)


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


class VerifyEmailView(View):
    def get(self, request, uidb64, token):
        user = None
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = CustomUser.objects.filter(pk=uid).first()
        except (TypeError, ValueError, OverflowError):
            user = None

        if user and default_token_generator.check_token(user, token):
            if not user.email_verified:
                user.email_verified = True
                user.save(update_fields=['email_verified'])
            messages.success(request, 'Your email has been verified successfully.')
        else:
            messages.error(request, 'This verification link is invalid or has expired.')

        if request.user.is_authenticated:
            return redirect(_get_authenticated_profile_url(request))
        return redirect('login')


class TwoFactorVerifyView(TemplateView):
    template_name = 'users/two_factor_verify.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('pending_2fa_user_id'):
            messages.info(request, 'Please sign in first.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pending_user = self._get_pending_user()
        pending_method = self.request.session.get('pending_2fa_method') or (pending_user.two_factor_method if pending_user else '')
        context.update({
            'form': kwargs.get('form') or TwoFactorCodeForm(),
            'pending_user': pending_user,
            'two_factor_method': pending_method,
        })
        return context

    def post(self, request, *args, **kwargs):
        user = self._get_pending_user()
        if not user:
            messages.error(request, 'Your login session expired. Please sign in again.')
            self._clear_pending_session()
            return redirect('login')

        action = request.POST.get('action')
        pending_method = request.session.get('pending_2fa_method') or _resolve_active_2fa_method(user)
        if action == 'resend_email_code':
            if pending_method != CustomUser.TWO_FACTOR_METHOD_EMAIL:
                messages.error(request, 'Email code is not enabled for this account.')
                return redirect('two_factor_verify')
            sent = _send_login_email_otp(user)
            if sent:
                messages.success(request, 'A new code has been sent to your email.')
            else:
                messages.error(request, 'Unable to send email code right now. Please try again later.')
            return redirect('two_factor_verify')

        form = TwoFactorCodeForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        submitted_code = form.cleaned_data['code']
        is_valid = False
        if pending_method == CustomUser.TWO_FACTOR_METHOD_EMAIL:
            is_valid = TwoFactorEmailCode.verify_latest_code(user, submitted_code)
        elif pending_method == CustomUser.TWO_FACTOR_METHOD_APP and user.two_factor_secret:
            is_valid = pyotp.TOTP(user.two_factor_secret).verify(submitted_code, valid_window=1)

        if not is_valid:
            form.add_error('code', 'Invalid or expired verification code.')
            return self.render_to_response(self.get_context_data(form=form))

        backend = request.session.get('pending_2fa_backend', 'django.contrib.auth.backends.ModelBackend')
        remember_me = bool(request.session.get('pending_2fa_remember_me'))
        next_url = request.session.get('pending_2fa_next') or reverse('home')

        login(request, user, backend=backend)
        _apply_login_side_effects(request, user, remember_me=remember_me)
        self._clear_pending_session()
        messages.success(request, 'Two-factor verification complete. Welcome back!')
        return HttpResponseRedirect(next_url)

    def _get_pending_user(self):
        pending_user_id = self.request.session.get('pending_2fa_user_id')
        if not pending_user_id:
            return None
        return CustomUser.objects.filter(pk=pending_user_id, is_active=True).first()

    def _clear_pending_session(self):
        for key in ['pending_2fa_user_id', 'pending_2fa_backend', 'pending_2fa_remember_me', 'pending_2fa_next', 'pending_2fa_method']:
            self.request.session.pop(key, None)
