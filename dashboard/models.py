from django.db import models


class MemberModerationAction(models.Model):
    ACTION_CHOICES = [
        ('warn', 'Warn'),
        ('ban', 'Ban'),
        ('unban', 'Unban'),
    ]

    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='moderation_actions')
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True)
    seen_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_moderation_actions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action}"