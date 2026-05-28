from django.conf import settings
from django.db import models


class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=150)
    bio = models.TextField(blank=True)
    focus = models.CharField(max_length=255, blank=True)
    badge = models.CharField(max_length=50, blank=True, help_text="Short label shown on the image (e.g. Founder, Programs)")
    photo = models.ImageField(upload_to='team_photos/', blank=True, null=True)
    linkedin_url = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    order = models.PositiveSmallIntegerField(default=0, help_text="Display order (lower = first)")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} – {self.role}"


class ChatbotConversation(models.Model):
    session_key = models.CharField(max_length=40, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message = models.TextField(blank=True)
    message_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat session {self.session_key} ({self.user or 'anonymous'})"


class ChatbotMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('bot', 'Bot'),
    ]

    conversation = models.ForeignKey(ChatbotConversation, related_name='messages', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    content = models.TextField()
    source = models.CharField(max_length=50, default='rule-based')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role} @ {self.created_at:%Y-%m-%d %H:%M}"


class ChatbotFaq(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    keywords = models.CharField(max_length=255, blank=True, help_text='Comma-separated keywords for matching')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['question']

    def keyword_list(self):
        return [keyword.strip().lower() for keyword in self.keywords.split(',') if keyword.strip()]

    def __str__(self):
        return self.question
