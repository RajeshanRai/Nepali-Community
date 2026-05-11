from django.contrib import admin
from .models import CustomUser, LoginActivity, TwoFactorEmailCode, RecentlyViewedContent, EmailVerificationToken
from django.contrib.auth.admin import UserAdmin


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('profile_picture', 'bio', 'birth_date', 'phone_number', 'location', 'country', 'address', 'recovery_email', 'recovery_phone', 'email_verified', 'two_factor_enabled', 'two_factor_enabled_at', 'two_factor_method', 'two_factor_secret', 'primary_community', 'secondary_community', 'is_verified_member', 'is_community_rep')}),
    )
    # Optimized: select_related to prevent N+1 when displaying community fields
    list_select_related = ('primary_community', 'secondary_community')


@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'device_label', 'logged_in_at')
    list_filter = ('logged_in_at',)
    search_fields = ('user__username', 'user__email', 'ip_address', 'user_agent')


@admin.register(TwoFactorEmailCode)
class TwoFactorEmailCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'expires_at', 'is_used')
    list_filter = ('created_at', 'expires_at', 'is_used')
    search_fields = ('user__username', 'user__email', 'code')


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'token', 'created_at', 'expires_at', 'is_used')
    list_filter = ('created_at', 'expires_at', 'is_used')
    search_fields = ('user__username', 'user__email', 'email', 'token')


@admin.register(RecentlyViewedContent)
class RecentlyViewedContentAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'title', 'url', 'viewed_at')
    list_filter = ('content_type', 'viewed_at')
    search_fields = ('user__username', 'user__email', 'title', 'url')
