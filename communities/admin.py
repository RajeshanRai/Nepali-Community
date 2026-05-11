from django.contrib import admin
from .models import Community, Committee


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_count', 'events_per_year')


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    list_display = ('community', 'name')
    # Optimized: select_related to prevent N+1 when displaying community names
    list_select_related = ('community',)
