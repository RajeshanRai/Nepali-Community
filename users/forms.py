from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


class CustomAuthForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Enter your username',
            'autocomplete': 'username',
            'class': 'auth-input',
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'class': 'auth-input',
        })

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password,
            )

            if self.user_cache is None:
                blocked_user = get_user_model()._default_manager.filter(
                    username__iexact=username,
                    is_active=False,
                ).first()
                if blocked_user:
                    raise ValidationError(
                        _('Your account has been banned due to a violation of our terms of service.\nIf you believe this is a mistake, please contact support.'),
                        code='banned_account',
                    )

                raise self.get_invalid_login_error()

            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class RegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'First name',
            'autocomplete': 'given-name',
            'class': 'auth-input',
        }),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last name',
            'autocomplete': 'family-name',
            'class': 'auth-input',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password',
            'class': 'auth-input',
        })
    )
    password_confirm = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Repeat your password',
            'autocomplete': 'new-password',
            'class': 'auth-input',
        })
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'email', 'password', 'password_confirm']
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'eg. raj_sharma',
                'autocomplete': 'username',
                'class': 'auth-input',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'you@example.com',
                'autocomplete': 'email',
                'class': 'auth-input',
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken. Please choose another.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email address already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                raise ValidationError(list(exc.messages))
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            'profile_picture',
            'first_name',
            'last_name',
            'username',
            'email',
            'bio',
            'phone_number',
            'birth_date',
            'location',
            'country',
            'address',
            'recovery_email',
            'recovery_phone',
            'primary_community',
            'secondary_community',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'profile-input', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'profile-input', 'placeholder': 'Last name'}),
            'username': forms.TextInput(attrs={'class': 'profile-input', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'profile-input', 'placeholder': 'Email address'}),
            'bio': forms.Textarea(attrs={'class': 'profile-textarea', 'placeholder': 'Tell the community a little about yourself', 'rows': 4}),
            'phone_number': forms.TextInput(attrs={'class': 'profile-input', 'placeholder': 'Phone number'}),
            'birth_date': forms.DateInput(attrs={'class': 'profile-input', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'profile-input', 'placeholder': 'City or region'}),
            'country': forms.TextInput(attrs={'class': 'profile-input', 'placeholder': 'Country'}),
            'address': forms.Textarea(attrs={'class': 'profile-textarea', 'placeholder': 'Address', 'rows': 3}),
            'recovery_email': forms.EmailInput(attrs={'class': 'profile-input', 'placeholder': 'Recovery email'}),
            'recovery_phone': forms.TextInput(attrs={'class': 'profile-input', 'placeholder': 'Recovery phone'}),
            'primary_community': forms.Select(attrs={'class': 'profile-select'}),
            'secondary_community': forms.Select(attrs={'class': 'profile-select'}),
            'profile_picture': forms.FileInput(attrs={'class': 'profile-file-input', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        self.fields['profile_picture'].help_text = 'Upload a square image for the best result.'

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken. Please choose another.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise ValidationError('An account with this email address already exists.')
        return email

    def clean_recovery_email(self):
        recovery_email = self.cleaned_data.get('recovery_email', '')
        email = self.cleaned_data.get('email', '')
        if recovery_email and email and recovery_email.strip().lower() == email.strip().lower():
            raise ValidationError('Use a different address for recovery email.')
        return recovery_email

    def save(self, commit=True):
        email_changed = False
        if self.instance.pk:
            email_changed = self.instance.email != self.cleaned_data.get('email')

        user = super().save(commit=False)
        if email_changed:
            user.email_verified = False

        if commit:
            user.save()
            self.save_m2m()
        return user


class ProfilePasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'class': 'profile-input', 'placeholder': 'Current password'})
        self.fields['new_password1'].widget.attrs.update({'class': 'profile-input', 'placeholder': 'New password'})
        self.fields['new_password2'].widget.attrs.update({'class': 'profile-input', 'placeholder': 'Confirm new password'})


class DeactivateAccountForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'profile-input', 'placeholder': 'Enter your password'}),
        help_text='Confirm your password before deactivating your account.',
    )
    confirm = forms.BooleanField(required=True)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.user.check_password(password):
            raise ValidationError('The password you entered is incorrect.')
        return password


class TwoFactorCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'auth-input',
            'placeholder': '6-digit code',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
        }),
    )

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip()
        if not code.isdigit():
            raise ValidationError('Enter a valid 6-digit numeric code.')
        return code


class AppTwoFactorSetupForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'profile-input',
            'placeholder': 'Authenticator code',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
        }),
    )

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip()
        if not code.isdigit():
            raise ValidationError('Enter a valid 6-digit authenticator code.')
        return code
