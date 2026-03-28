from django.db import models


class Donation(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('interact', 'Interact e-Transfer'),
        ('card', 'Credit/Debit Card'),
    ]
    
    DONATION_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    purpose = models.CharField(max_length=200, blank=True)
    anonymous = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='interact')
    status = models.CharField(max_length=20, choices=DONATION_STATUS, default='pending')
    donor_name = models.CharField(max_length=150, blank=True)
    donor_email = models.EmailField(blank=True)
    donor_phone = models.CharField(max_length=30, blank=True)
    donor_address_line1 = models.CharField(max_length=255, blank=True)
    donor_city = models.CharField(max_length=100, blank=True)
    donor_province = models.CharField(max_length=100, blank=True)
    donor_postal_code = models.CharField(max_length=20, blank=True)
    interact_email = models.EmailField(blank=True, help_text="Email for Interact e-Transfer")
    card_last_four = models.CharField(max_length=4, blank=True, help_text="Last 4 digits of card")
    transaction_ref = models.CharField(max_length=100, blank=True, unique=True)
    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{'Anonymous' if self.anonymous else (self.donor_name or self.user)} - ${self.amount}"


class StripeWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type or 'unknown'} ({self.event_id})"

