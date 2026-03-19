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
