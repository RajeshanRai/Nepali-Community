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
    interact_email = models.EmailField(blank=True, help_text="Email for Interact e-Transfer")
    card_last_four = models.CharField(max_length=4, blank=True, help_text="Last 4 digits of card")
    transaction_ref = models.CharField(max_length=100, blank=True, unique=True)

    def __str__(self):
        return f"{'Anonymous' if self.anonymous else (self.donor_name or self.user)} - ${self.amount}"

