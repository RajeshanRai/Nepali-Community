from django.contrib import admin
from .models import Program, EventRegistration, RequestEvent
from django.utils import timezone
from django.utils.html import format_html


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:40px; max-width:80px; object-fit:cover; border-radius:4px;" />', obj.image.url)
        return '-'
    display_image.short_description = 'Image'

    list_display = ('display_image', 'title', 'community', 'date', 'event_type', 'registered_count', 'max_attendees', 'waitlist_enabled', 'registration_status_badge')
    list_editable = ('max_attendees',)
    list_filter = ('event_type', 'community')
    search_fields = ('title', 'location', 'live_stream_url')
    # Optimized: select_related to prevent N+1 when displaying community names
    list_select_related = ('community',)

    # include waitlist_enabled and show registered_count as readonly in the form
    fields = ('community', 'title', 'description', 'location', 'date', 'start_time', 'ticket_info', 'event_type', 'image', 'is_virtual', 'max_attendees', 'registered_count', 'waitlist_enabled', 'registration_closed')
    readonly_fields = ('registered_count',)

    def registration_status_badge(self, obj):
        status = getattr(obj, 'registration_status', 'open')
        label = getattr(obj, 'registration_status_label', '')
        css = getattr(obj, 'registration_status_class', '')
        color = '#28a745' if status == 'open' else ('#dc3545' if status == 'event_closed' else ('#ffc107' if status == 'full' else '#6c757d'))
        return format_html('<span style="display:inline-block;padding:4px 8px;border-radius:6px;background:{};color:#fff;font-weight:600;">{}</span>', color, label)
    registration_status_badge.short_description = 'Status'

    def total_attended(self, obj):
        return obj.registered_count or 0
    total_attended.short_description = 'Total attended'


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'guest_name', 'guest_email', 'guest_phone', 'program', 'registered_at')
    list_filter = ('program',)
    search_fields = ('guest_name', 'guest_email', 'user__username')
    # Optimized: select_related to prevent N+1 when displaying user and program names
    list_select_related = ('user', 'program')


from .models import WaitlistEntry


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'guest_name', 'guest_email', 'program', 'created_at')
    list_filter = ('program',)
    search_fields = ('guest_name', 'guest_email', 'user__username')
    list_select_related = ('user', 'program')


@admin.register(RequestEvent)
class RequestEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'requester_name', 'status', 'date', 'submitted_at', 'created_program')
    list_filter = ('status', 'submitted_at')
    search_fields = ('title', 'requester_name', 'requester_email')
    readonly_fields = ('submitted_at', 'approved_at', 'created_program')
    # Optimized: select_related to prevent N+1 when displaying related objects
    list_select_related = ('requester', 'community', 'approved_by', 'created_program')
    actions = ['approve_requests', 'reject_requests']
    
    fieldsets = (
        ('Request Details', {
            'fields': ('title', 'description', 'location', 'date', 'event_type', 'community', 'target_attendees')
        }),
        ('Requester Information', {
            'fields': ('requester', 'requester_name', 'requester_email', 'requester_phone')
        }),
        ('Status & Approval', {
            'fields': ('status', 'submitted_at', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Program Link', {
            'fields': ('created_program',),
            'classes': ('collapse',)
        }),
    )
    
    def approve_requests(self, request, queryset):
        """Admin action to approve requests and create programs"""
        approved_count = 0
        error_count = 0
        
        for req in queryset.filter(status='pending'):
            try:
                # Validate required fields before approval
                if not req.community:
                    self.message_user(request, f'Cannot approve "{req.title}": Community is required', level='error')
                    error_count += 1
                    continue
                if not req.date:
                    self.message_user(request, f'Cannot approve "{req.title}": Date is required', level='error')
                    error_count += 1
                    continue
                
                req.status = 'approved'
                req.approved_by = request.user
                req.approved_at = timezone.now()
                req.save()
                
                # Convert to program
                program = req.convert_to_program(request.user)
                self.message_user(request, f'✓ Approved "{req.title}" and created program', level='success')
                approved_count += 1
            except Exception as e:
                self.message_user(request, f'Error approving "{req.title}": {str(e)}', level='error')
                error_count += 1
        
        if approved_count > 0:
            self.message_user(request, f'Successfully approved {approved_count} request(s)', level='success')
        if error_count > 0:
            self.message_user(request, f'{error_count} request(s) could not be approved', level='warning')
    
    approve_requests.short_description = "Approve selected requests and create programs"
    
    def reject_requests(self, request, queryset):
        """Admin action to reject requests"""
        updated = queryset.filter(status='pending').update(
            status='rejected',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'Rejected {updated} request(s)')
    
    reject_requests.short_description = "Reject selected requests"
