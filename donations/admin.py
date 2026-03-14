from django.contrib import admin
from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'is_recurring', 'purpose', 'created_at')
    # Optimized: select_related to prevent N+1 when displaying user names
    list_select_related = ('user',)
