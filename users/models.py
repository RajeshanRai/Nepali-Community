from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets
import uuid


class CustomUser(AbstractUser):
    TWO_FACTOR_METHOD_NONE = 'none'
    TWO_FACTOR_METHOD_EMAIL = 'email'
    TWO_FACTOR_METHOD_APP = 'app'
    TWO_FACTOR_METHOD_CHOICES = [
        (TWO_FACTOR_METHOD_NONE, 'Disabled'),
        (TWO_FACTOR_METHOD_EMAIL, 'Email code'),
        (TWO_FACTOR_METHOD_APP, 'Authenticator app'),
    ]

    # additional fields
    birth_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=120, blank=True)
    recovery_email = models.EmailField(blank=True)
    recovery_phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_enabled_at = models.DateTimeField(null=True, blank=True)
    two_factor_method = models.CharField(max_length=20, blank=True)
    two_factor_secret = models.CharField(max_length=64, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    primary_community = models.ForeignKey(
        'communities.Community',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='primary_members'
    )
    secondary_community = models.ForeignKey(
        'communities.Community',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='secondary_members'
    )
    # roles
    is_verified_member = models.BooleanField(default=False)
    is_community_rep = models.BooleanField(default=False)

    @property
    def display_name(self):
        full_name = self.get_full_name().strip()
        return full_name or self.username

    @property
    def initials(self):
        source = self.display_name.split()
        if len(source) >= 2:
            return f'{source[0][0]}{source[1][0]}'.upper()
        return (self.display_name[:2] or self.username[:2]).upper()

    def __str__(self):
        return self.username


class LoginActivity(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='login_activities')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    logged_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-logged_in_at']
        verbose_name_plural = 'Login activities'

    @property
    def device_label(self):
        agent = (self.user_agent or '').lower()
        if 'iphone' in agent or 'ios' in agent:
            return 'iPhone'
        if 'ipad' in agent:
            return 'iPad'
        if 'android' in agent:
            return 'Android device'
        if 'windows' in agent:
            return 'Windows device'
        if 'mac os' in agent or 'macintosh' in agent:
            return 'Mac device'
        if 'linux' in agent:
            return 'Linux device'
        return 'Unknown device'

    def __str__(self):
        return f'{self.user.username} @ {self.logged_in_at:%Y-%m-%d %H:%M}'


class EmailVerificationToken(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='email_verification_tokens')
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def create_for_user(cls, user, lifetime_hours=24):
        return cls.objects.create(
            user=user,
            email=user.email,
            expires_at=timezone.now() + timedelta(hours=lifetime_hours),
        )

    def is_valid(self):
        return (not self.is_used) and timezone.now() <= self.expires_at


class TwoFactorEmailCode(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='two_factor_email_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def create_for_user(cls, user, lifetime_minutes=10):
        code = ''.join(secrets.choice('0123456789') for _ in range(6))
        return cls.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=lifetime_minutes),
        )

    @classmethod
    def verify_latest_code(cls, user, code):
        record = cls.objects.filter(
            user=user,
            is_used=False,
        ).order_by('-created_at').first()

        if not record:
            return False
        if timezone.now() > record.expires_at:
            return False
        if str(code).strip() != record.code:
            return False

        record.is_used = True
        record.save(update_fields=['is_used'])
        return True

    def __str__(self):
        return f'{self.user.username} email 2FA code'


class RecentlyViewedContent(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='recently_viewed_content')
    content_type = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']
        unique_together = ('user', 'content_type', 'object_id')

    def __str__(self):
        return f'{self.user.username} viewed {self.content_type}: {self.title}'
