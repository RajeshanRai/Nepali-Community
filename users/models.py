from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    # additional fields
    birth_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    primary_community = models.ForeignKey(
        'communities.Community',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='primary_members'
    )
    secondary_community = models.ForeignKey(
        'communities.Community',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='secondary_members'
    )
    # roles
    is_verified_member = models.BooleanField(default=False)
    is_community_rep = models.BooleanField(default=False)

    def __str__(self):
        return self.username
