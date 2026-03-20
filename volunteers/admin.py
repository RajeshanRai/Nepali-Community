from django.contrib import admin
from django.utils import timezone
from .models import VolunteerOpportunity, VolunteerApplication, VolunteerRequest


@admin.register(VolunteerOpportunity)
class VolunteerOpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'positions_remaining', 'positions_needed', 'start_date', 'is_remote', 'created_at')
    list_filter = ('status', 'category', 'is_remote', 'created_at')
    # Optimized: select_related to prevent N+1 when accessing created_by field
    list_select_related = ('created_by',)
    search_fields = ('title', 'description', 'requirements')
    readonly_fields = ('created_at', 'updated_at', 'positions_remaining')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'status')
        }),
        ('Location & Time', {
            'fields': ('location', 'is_remote', 'start_date', 'end_date', 'time_commitment')
        }),
        ('Positions', {
            'fields': ('positions_needed', 'positions_filled', 'positions_remaining')
        }),
        ('Additional Details', {
            'fields': ('requirements', 'benefits', 'contact_email', 'contact_phone')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'opportunity', 'email', 'status', 'applied_at', 'reviewed_at')
    list_filter = ('status', 'applied_at', 'opportunity__category')
    search_fields = ('name', 'email', 'opportunity__title', 'motivation')
    # Optimized: select_related to prevent N+1 when displaying opportunity, applicant, and reviewed_by
    list_select_related = ('opportunity', 'applicant', 'reviewed_by')
    readonly_fields = ('applied_at', 'reviewed_at')
    actions = ['approve_applications', 'reject_applications']
    
    fieldsets = (
        ('Application Info', {
            'fields': ('opportunity', 'status')
        }),
        ('Applicant Details', {
            'fields': ('applicant', 'name', 'email', 'phone')
        }),
        ('Application Content', {
            'fields': ('motivation', 'experience', 'availability')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'admin_notes')
        }),
    )
    
    def approve_applications(self, request, queryset):
        """Approve selected applications"""
        approved_count = 0
        for application in queryset.filter(status='pending'):
            application.status = 'accepted'
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.save()
            
            # Update positions filled
            opportunity = application.opportunity
            if opportunity.positions_filled < opportunity.positions_needed:
                opportunity.positions_filled += 1
                if opportunity.positions_filled >= opportunity.positions_needed:
                    opportunity.status = 'filled'
                opportunity.save()
            
            approved_count += 1
        
        self.message_user(request, f'Successfully approved {approved_count} application(s)', level='success')
    
    approve_applications.short_description = "Approve selected applications"
    
    def reject_applications(self, request, queryset):
        """Reject selected applications"""
        updated = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'Rejected {updated} application(s)')
    
    reject_applications.short_description = "Reject selected applications"


@admin.register(VolunteerRequest)
class VolunteerRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'volunteer_type', 'email', 'phone', 'status', 'created_at')
    list_filter = ('volunteer_type', 'status', 'created_at')
    search_fields = ('name', 'email', 'phone', 'address', 'expertise', 'purpose')
    readonly_fields = ('created_at', 'reviewed_at')
