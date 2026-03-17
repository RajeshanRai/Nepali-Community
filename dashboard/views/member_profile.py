import base64
import io

import pyotp
import qrcode  # pyright: ignore[reportMissingImports]

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, IntegerField, Value, When
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import TemplateView

from users.forms import (
    AppTwoFactorSetupForm,
    DeactivateAccountForm,
    ProfilePasswordChangeForm,
    ProfileUpdateForm,
)
from users.models import CustomUser
from users.views import (
    _resolve_active_2fa_method,
    _send_verification_email,
)


def _dash_qr(totp_uri):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')
    with io.BytesIO() as buf:
        image.save(buf, format='PNG')
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


@login_required
def dashboard_home(request):
    if request.user.is_superuser:
        return redirect('dashboard:profiles')
    return redirect('profile')


class DashboardProfilesView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/users/profiles.html'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_staff):
            return redirect('profile')
        self.target_user = self._get_target_user()
        return super().dispatch(request, *args, **kwargs)

    def _get_target_user(self):
        user_id = self.kwargs.get('user_id')
        if user_id:
            return get_object_or_404(CustomUser, pk=user_id)
        return self.request.user

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _redirect(self):
        if self.target_user.pk == self.request.user.pk:
            return redirect('dashboard:profiles')
        return redirect('dashboard:profiles_detail', user_id=self.target_user.pk)

    def _ctx(self, **extra):
        """Build full context, optionally overriding form instances."""
        user = self.target_user
        active_2fa = _resolve_active_2fa_method(user)
        location_parts = [p for p in [user.location, user.country] if p]
        viewing_self = user.pk == self.request.user.pk

        pending_totp_secret = None
        pending_totp_user_id = self.request.session.get('pending_totp_user_id')
        if pending_totp_user_id == user.pk:
            pending_totp_secret = self.request.session.get('pending_totp_secret')
        totp_qr_data_uri = None
        if pending_totp_secret:
            issuer = 'Nepali Community of Vancouver'
            account_name = user.email or user.username
            totp_uri = pyotp.TOTP(pending_totp_secret).provisioning_uri(name=account_name, issuer_name=issuer)
            totp_qr_data_uri = _dash_qr(totp_uri)

        ctx = {
            'profile_user': user,
            'viewing_self': viewing_self,
            'login_activity': user.login_activities.all()[:10],
            'active_2fa_method': active_2fa,
            'display_location': ', '.join(location_parts),
            'groups': user.groups.all(),
            'all_users': CustomUser.objects.annotate(
                admin_first=Case(
                    When(pk=self.request.user.pk, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                username_sort=Lower('username'),
            ).order_by('admin_first', 'username_sort'),
            'deactivated_users': CustomUser.objects.filter(is_active=False).order_by('-date_joined')[:20],
            # forms
            'profile_form': extra.pop('profile_form', None) or ProfileUpdateForm(instance=user),
            'password_form': extra.pop('password_form', None) or (ProfilePasswordChangeForm(user=user) if viewing_self else None),
            'deactivate_form': extra.pop('deactivate_form', None) or (DeactivateAccountForm(user=user) if viewing_self else None),
            'app_2fa_form': extra.pop('app_2fa_form', None) or AppTwoFactorSetupForm(),
            # 2FA setup state
            'pending_totp_secret': pending_totp_secret,
            'totp_qr_data_uri': totp_qr_data_uri,
            # which panel to open after a form error
            'open_panel': extra.pop('open_panel', ''),
        }
        ctx.update(extra)
        return ctx

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self._ctx(**kwargs))
        return ctx

    # ------------------------------------------------------------------
    # POST dispatch
    # ------------------------------------------------------------------

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        target = self.target_user

        # --- basic profile info ---
        if action == 'update_profile':
            form = ProfileUpdateForm(request.POST, request.FILES, instance=target)
            if form.is_valid():
                previous_email = target.email
                user = form.save()
                messages.success(request, 'Profile updated successfully.')
                if previous_email != user.email:
                    _send_verification_email(request, user)
                    if user.two_factor_method == CustomUser.TWO_FACTOR_METHOD_EMAIL:
                        user.two_factor_method = CustomUser.TWO_FACTOR_METHOD_NONE
                        user.two_factor_enabled = False
                        user.two_factor_enabled_at = None
                        user.save(update_fields=['two_factor_method', 'two_factor_enabled', 'two_factor_enabled_at'])
                        messages.warning(request, 'Email-based 2FA was disabled because your email changed.')
                    messages.info(request, 'A verification email was sent to the new address.')
                return self._redirect()
            return self.render_to_response(self.get_context_data(profile_form=form, open_panel='edit'))

        # --- resend verification ---
        if action == 'resend_verification_email':
            if target.email_verified:
                messages.info(request, 'Your email is already verified.')
            elif not target.email:
                messages.error(request, 'Add an email address first.')
            else:
                sent = _send_verification_email(request, target)
                if sent:
                    messages.success(request, 'Verification email sent.')
                else:
                    messages.error(request, 'Could not send verification email right now.')
            return self._redirect()

        # --- password change ---
        if action == 'change_password':
            if target.pk != request.user.pk:
                messages.error(request, 'Password can only be changed on your own profile page.')
                return self._redirect()
            form = ProfilePasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully.')
                return self._redirect()
            return self.render_to_response(self.get_context_data(password_form=form, open_panel='password'))

        # --- deactivate own account ---
        if action == 'deactivate_account':
            if target.pk != request.user.pk:
                messages.error(request, 'Open your own profile page to deactivate your account.')
                return self._redirect()
            form = DeactivateAccountForm(request.user, request.POST)
            if form.is_valid():
                request.user.is_active = False
                request.user.save(update_fields=['is_active'])
                logout(request)
                messages.success(request, 'Your account has been deactivated.')
                return redirect('home')
            return self.render_to_response(self.get_context_data(deactivate_form=form, open_panel='danger'))

        # --- admin deactivate selected account ---
        if action == 'deactivate_selected_account':
            if target.pk == request.user.pk:
                messages.error(request, 'Use the self deactivation form for your own account.')
                return self._redirect()
            if not target.is_active:
                messages.info(request, 'This account is already deactivated.')
                return self._redirect()
            target.is_active = False
            target.save(update_fields=['is_active'])
            messages.success(request, f'Account deactivated for {target.username}.')
            return self._redirect()

        # --- reactivate another inactive user ---
        if action == 'reactivate_account':
            user_id = request.POST.get('user_id')
            target = CustomUser.objects.filter(pk=user_id, is_active=False).first()
            if not target:
                messages.error(request, 'Selected account is not available for reactivation.')
                return self._redirect()
            target.is_active = True
            target.save(update_fields=['is_active'])
            messages.success(request, f'Account reactivated for {target.username}.')
            return self._redirect()

        # --- 2FA: enable email ---
        if action == 'enable_email_2fa':
            if not target.email:
                messages.error(request, 'Add an email address before enabling email-based 2FA.')
            elif not target.email_verified:
                messages.error(request, 'Verify your email first before enabling email-based 2FA.')
            else:
                u = target
                u.two_factor_method = CustomUser.TWO_FACTOR_METHOD_EMAIL
                u.two_factor_secret = ''
                u.two_factor_enabled = True
                u.two_factor_enabled_at = timezone.now()
                u.save(update_fields=['two_factor_method', 'two_factor_secret', 'two_factor_enabled', 'two_factor_enabled_at'])
                request.session.pop('pending_totp_secret', None)
                request.session.pop('pending_totp_user_id', None)
                messages.success(request, 'Email-based 2FA enabled.')
            return self._redirect()

        # --- 2FA: start app setup ---
        if action == 'start_app_2fa_setup':
            request.session['pending_totp_secret'] = pyotp.random_base32()
            request.session['pending_totp_user_id'] = target.pk
            messages.info(request, 'Scan the QR code with your authenticator app, then enter the code below.')
            return self._redirect()

        # --- 2FA: confirm app setup ---
        if action == 'confirm_app_2fa_setup':
            secret = request.session.get('pending_totp_secret')
            pending_totp_user_id = request.session.get('pending_totp_user_id')
            form = AppTwoFactorSetupForm(request.POST)
            if not secret or pending_totp_user_id != target.pk:
                messages.error(request, 'Start authenticator setup first.')
                return self._redirect()
            if form.is_valid():
                otp = form.cleaned_data['code']
                if pyotp.TOTP(secret).verify(otp, valid_window=1):
                    u = target
                    u.two_factor_secret = secret
                    u.two_factor_method = CustomUser.TWO_FACTOR_METHOD_APP
                    u.two_factor_enabled = True
                    u.two_factor_enabled_at = timezone.now()
                    u.save(update_fields=['two_factor_secret', 'two_factor_method', 'two_factor_enabled', 'two_factor_enabled_at'])
                    request.session.pop('pending_totp_secret', None)
                    request.session.pop('pending_totp_user_id', None)
                    messages.success(request, 'Authenticator app 2FA enabled.')
                    return self._redirect()
                form.add_error('code', 'Invalid code. Please try again.')
            return self.render_to_response(self.get_context_data(app_2fa_form=form, open_panel='2fa'))

        # --- 2FA: disable ---
        if action == 'disable_2fa':
            u = target
            u.two_factor_method = CustomUser.TWO_FACTOR_METHOD_NONE
            u.two_factor_secret = ''
            u.two_factor_enabled = False
            u.two_factor_enabled_at = None
            u.save(update_fields=['two_factor_method', 'two_factor_secret', 'two_factor_enabled', 'two_factor_enabled_at'])
            request.session.pop('pending_totp_secret', None)
            request.session.pop('pending_totp_user_id', None)
            messages.success(request, '2FA has been disabled.')
            return self._redirect()

        messages.error(request, 'Unknown action.')
        return self._redirect()
