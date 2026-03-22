from django.db import models


class Program(models.Model):
    EVENT_TYPES = [
        ('cultural', 'Cultural'),
        ('workshop', 'Workshop'),
        ('meeting', 'Meeting'),
        ('festival', 'Festival'),
        ('other', 'Other'),
    ]

    community = models.ForeignKey('communities.Community', on_delete=models.CASCADE, related_name='programs')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=300, blank=True)
    live_stream_url = models.URLField(blank=True)
    is_virtual = models.BooleanField(default=False)
    date = models.DateField()
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='other')

    likes = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    registered_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} ({self.date})"


class EventRegistration(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='registrations')
    
    # Guest registration fields (for non-logged-in users)
    guest_name = models.CharField(max_length=200, blank=True)
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=20, blank=True)
    
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'program'], name='unique_user_program')
        ]
        # guests with same email should not register twice for same program
        # email may be blank for authenticated registrations
        constraints += [
            models.UniqueConstraint(fields=['guest_email', 'program'], name='unique_guest_email_program', condition=~models.Q(guest_email=""))
        ]


class RequestEvent(models.Model):
    """Model to store event requests submitted by users or guests"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    EVENT_TYPE_CHOICES = [
        ('festival', 'Festival'),
        ('workshop', 'Workshop'),
        ('meeting', 'Meeting'),
        ('cultural', 'Cultural'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=300, blank=True)
    date = models.DateField(null=True, blank=True)
    target_attendees = models.PositiveIntegerField(null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, default='other')
    community = models.ForeignKey('communities.Community', null=True, blank=True, on_delete=models.SET_NULL)

    # requester info
    requester = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL)
    requester_name = models.CharField(max_length=200, blank=True)
    requester_email = models.EmailField(blank=True)
    requester_phone = models.CharField(max_length=30, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # approval tracking
    approved_by = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_requests')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # link to created program if approved
    created_program = models.OneToOneField(Program, null=True, blank=True, on_delete=models.SET_NULL, related_name='request_event')

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Request: {self.title} ({self.status}) - {self.submitted_at.date()}"
    
    def convert_to_program(self, user):
        """Convert approved request to a Program object"""
        if self.status != 'approved':
            raise ValueError("Only approved requests can be converted to programs")
        
        # Validate required fields
        if not self.community:
            raise ValueError("Community is required to create a program")
        if not self.date:
            raise ValueError("Date is required to create a program")
        
        # Don't create duplicate programs
        if self.created_program:
            return self.created_program
        
        program = Program(
            title=self.title,
            description=self.description,
            location=self.location,
            date=self.date,
            event_type=self.event_type,
            community=self.community,
                # created_by=user
        )
        program.save()
        self.created_program = program
        self.save()
        return program
