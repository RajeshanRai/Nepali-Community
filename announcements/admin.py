from django.contrib import admin
from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'priority', 'is_active', 'is_pinned', 'show_on_homepage', 'publish_date', 'expire_date', 'views_count')
    list_filter = ('category', 'priority', 'is_active', 'is_pinned', 'show_on_homepage', 'publish_date')
    # Optimized: select_related to prevent N+1 when accessing created_by field
    list_select_related = ('created_by',)
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at', 'views_count')
    list_editable = ('is_active', 'is_pinned', 'show_on_homepage')
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'content', 'category', 'priority')
        }),
        ('Link (Optional)', {
            'fields': ('link_url', 'link_text'),
            'classes': ('collapse',)
        }),
        ('Display Settings', {
            'fields': ('is_active', 'show_on_homepage', 'is_pinned')
        }),
        ('Schedule', {
            'fields': ('publish_date', 'expire_date'),
            'description': 'Control when this announcement appears'
        }),
        ('Statistics & Metadata', {
            'fields': ('views_count', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
