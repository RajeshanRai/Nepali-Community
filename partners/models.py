from django.db import models


class Partner(models.Model):
    name = models.CharField(max_length=300)
    logo = models.ImageField(upload_to='partner_logos/', null=True, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    partnership_since = models.DateField(null=True, blank=True)
    social_links = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name
