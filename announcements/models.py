from django.db import models
from django.utils import timezone


class Announcement(models.Model):
    """Model for community announcements"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('event', 'Event'),
        ('emergency', 'Emergency'),
        ('opportunity', 'Opportunity'),
        ('update', 'Update'),
        ('news', 'News'),
    ]
    
    title = models.CharField(max_length=300)
    content = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Optional fields
    link_url = models.URLField(blank=True, help_text="External link for more info")
    link_text = models.CharField(max_length=100, blank=True, help_text="Text for the link button")
    
    # Display settings
    is_active = models.BooleanField(default=True)
    show_on_homepage = models.BooleanField(default=False, help_text="Display on homepage")
    is_pinned = models.BooleanField(default=False, help_text="Pin to top of announcements")
    
    # Scheduling
    publish_date = models.DateTimeField(default=timezone.now)
    expire_date = models.DateTimeField(null=True, blank=True, help_text="Auto-hide after this date")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='announcements')
    
    # Stats
    views_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-is_pinned', '-priority', '-publish_date']
    
    def __str__(self):
        return f"{self.title} ({self.priority})"
    
    @property
    def is_published(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.publish_date > now:
            return False
        if self.expire_date and self.expire_date < now:
            return False
        return True
    
    @property
    def is_expired(self):
        if self.expire_date and timezone.now() > self.expire_date:
            return True
        return False
