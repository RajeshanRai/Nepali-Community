from django.db import models
from django.utils import timezone


class VolunteerOpportunity(models.Model):
    """Model for volunteer opportunities"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('filled', 'Filled'),
    ]
    
    CATEGORY_CHOICES = [
        ('event', 'Event Support'),
        ('education', 'Education & Tutoring'),
        ('translation', 'Translation'),
        ('technology', 'Technology'),
        ('fundraising', 'Fundraising'),
        ('outreach', 'Community Outreach'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=300)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    location = models.CharField(max_length=300, blank=True)
    is_remote = models.BooleanField(default=False)
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    time_commitment = models.CharField(max_length=200, blank=True, help_text="e.g., 5 hours/week, One-time event")
    
    positions_needed = models.PositiveIntegerField(default=1)
    positions_filled = models.PositiveIntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    
    requirements = models.TextField(blank=True, help_text="Skills or requirements needed")
    benefits = models.TextField(blank=True, help_text="What volunteers will gain")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_opportunities')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Volunteer Opportunities'
    
    def __str__(self):
        return f"{self.title} ({self.status})"
    
    @property
    def positions_remaining(self):
        return max(0, self.positions_needed - self.positions_filled)
    
    @property
    def is_active(self):
        return self.status == 'open' and self.positions_remaining > 0


class VolunteerApplication(models.Model):
    """Model for volunteer applications"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    opportunity = models.ForeignKey(VolunteerOpportunity, on_delete=models.CASCADE, related_name='applications')
    
    # Applicant info
    applicant = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='volunteer_applications')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    
    # Application details
    motivation = models.TextField(help_text="Why do you want to volunteer?")
    experience = models.TextField(blank=True, help_text="Relevant experience or skills")
    availability = models.TextField(blank=True, help_text="When are you available?")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_applications')
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['opportunity', 'email']
    
    def __str__(self):
        return f"{self.name} - {self.opportunity.title} ({self.status})"


class VolunteerRequest(models.Model):
    """Model for general volunteer requests from the volunteer page"""

    VOLUNTEER_TYPE_CHOICES = [
        ('general', 'General Volunteer'),
        ('expertise', 'Expertise-based Volunteer'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('contacted', 'Contacted'),
        ('closed', 'Closed'),
    ]

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30)
    email = models.EmailField()
    address = models.CharField(max_length=300)

    volunteer_type = models.CharField(max_length=20, choices=VOLUNTEER_TYPE_CHOICES, default='general')
    expertise = models.CharField(max_length=200, blank=True, help_text='Relevant skill area for expertise volunteers')
    schedule_availability = models.CharField(max_length=250, help_text='When you are available to volunteer')
    purpose = models.TextField(help_text='Why do you want to volunteer?')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_volunteer_type_display()})"
