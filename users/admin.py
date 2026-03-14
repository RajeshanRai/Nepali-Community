from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('birth_date', 'phone_number', 'address', 'primary_community', 'secondary_community', 'is_verified_member', 'is_community_rep')}),
    )
    # Optimized: select_related to prevent N+1 when displaying community fields
    list_select_related = ('primary_community', 'secondary_community')
