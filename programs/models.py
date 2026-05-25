from django.db import models
from django.utils import timezone


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
    start_time = models.TimeField('Start time', null=True, blank=True)
    ticket_info = models.CharField('Tickets', max_length=100, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='other')
    image = models.ImageField(upload_to='program_images/', blank=True, null=True, help_text='Primary image used on the program detail and for social sharing')

    likes = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    registered_count = models.PositiveIntegerField(default=0)
    max_attendees = models.PositiveIntegerField(null=True, blank=True, help_text='Optional maximum attendees for the event')
    registration_closed = models.BooleanField(default=False, help_text='Admin can manually close registrations')
    waitlist_enabled = models.BooleanField(default=False, help_text='Allow users to join a waitlist when the event is full')

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def seats_remaining(self):
        if self.max_attendees is None:
            return None
        return max(0, self.max_attendees - (self.registered_count or 0))

    @property
    def is_full(self):
        if self.max_attendees is None:
            return False
        return (self.registered_count or 0) >= self.max_attendees

    @property
    def registration_status(self):
        """Return one of: 'event_closed', 'registration_closed', 'full', 'open'"""
        try:
            if self.date < timezone.localdate():
                return 'event_closed'
        except Exception:
            pass
        if self.registration_closed:
            return 'registration_closed'
        if self.is_full:
            return 'full'
        return 'open'

    @property
    def registration_status_label(self):
        labels = {
            'event_closed': 'Event closed',
            'registration_closed': 'Registration closed',
            'full': 'Registration full',
            'open': 'Open',
        }
        return labels.get(self.registration_status, 'Open')

    @property
    def registration_status_class(self):
        classes = {
            'event_closed': 'status--danger',
            'registration_closed': 'status--muted',
            'full': 'status--warning',
            'open': 'status--success',
        }
        return classes.get(self.registration_status, 'status--success')

    def promote_from_waitlist(self):
        """Promote the oldest waitlist entry into a confirmed registration if seats are available."""
        # Import here to avoid circular references at file import time
        from django.db import transaction
        try:
            entry = self.waitlist_entries.order_by('created_at').first()
            if not entry:
                return None
            if self.is_full:
                return None

            with transaction.atomic():
                # create a registration from the waitlist entry
                reg_kwargs = {'program': self}
                if entry.user:
                    reg_kwargs['user'] = entry.user
                else:
                    reg_kwargs['guest_name'] = entry.guest_name
                    reg_kwargs['guest_email'] = entry.guest_email
                    reg_kwargs['guest_phone'] = entry.guest_phone

                EventRegistration = globals().get('EventRegistration')
                if EventRegistration is None:
                    # fallback import
                    from .models import EventRegistration as EventRegistrationClass
                    EventRegistration = EventRegistrationClass

                registration = EventRegistration.objects.create(**reg_kwargs)
                self.registered_count = (self.registered_count or 0) + 1
                self.save()
                entry.delete()
                return registration
        except Exception:
            return None


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


class WaitlistEntry(models.Model):
    """Users or guests who joined the waitlist for a program when it is full."""
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='waitlist_entries')

    guest_name = models.CharField(max_length=200, blank=True)
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'program'], name='unique_waitlist_user_program'),
            models.UniqueConstraint(fields=['guest_email', 'program'], name='unique_waitlist_guest_email_program', condition=~models.Q(guest_email="")),
        ]

    def __str__(self):
        if self.user:
            return f"Waitlist: {self.user} -> {self.program.title}"
        return f"Waitlist: {self.guest_name or 'Guest'} ({self.guest_email}) -> {self.program.title}"


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
