from django.db import models


class Community(models.Model):
    name = models.CharField(max_length=200, unique=True)
    icon = models.ImageField(upload_to='community_icons/', null=True, blank=True)
    introduction = models.TextField(blank=True)
    member_count = models.PositiveIntegerField(default=0)
    events_per_year = models.PositiveIntegerField(default=0)
    cultural_objects = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name


class Committee(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='committees')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.community.name} - {self.name}"
