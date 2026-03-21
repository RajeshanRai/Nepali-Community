from django.contrib import admin
from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'donor_name',
        'amount',
        'payment_method',
        'status',
        'card_last_four',
        'transaction_ref',
        'created_at',
    )
    search_fields = ('donor_name', 'donor_email', 'transaction_ref', 'card_last_four')
    list_filter = ('payment_method', 'status', 'is_recurring', 'created_at')
    # Optimized: select_related to prevent N+1 when displaying user names
    list_select_related = ('user',)
