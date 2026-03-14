from django import forms
from .models import Donation


class DonationForm(forms.ModelForm):
    donation_amount = forms.ChoiceField(
        choices=[
            ('20', 'Supporter - $20'),
            ('50', 'Friend - $50'),
            ('100', 'Patron - $100'),
            ('custom', 'Custom Amount'),
        ],
        widget=forms.RadioSelect,
        label="Select Donation Tier",
        required=True
    )
    custom_amount = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Enter custom amount',
            'class': 'form-control',
            'style': 'display: none;'
        }),
        required=False,
        label="Custom Amount"
    )
    
    payment_method = forms.ChoiceField(
        choices=[
            ('interact', 'Interact e-Transfer'),
            ('card', 'Credit/Debit Card'),
        ],
        widget=forms.RadioSelect,
        label="Select Payment Method",
        required=True,
        initial='interact'
    )
    
    # Card fields (optional, only used for card payment)
    card_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Name on Card',
            'class': 'form-control',
        }),
        required=False,
        label="Name on Card"
    )
    
    card_number = forms.CharField(
        max_length=19,
        widget=forms.TextInput(attrs={
            'placeholder': '1234 5678 9012 3456',
            'class': 'form-control',
            'inputmode': 'numeric',
        }),
        required=False,
        label="Card Number"
    )
    
    card_expiry = forms.CharField(
        max_length=5,
        widget=forms.TextInput(attrs={
            'placeholder': 'MM/YY',
            'class': 'form-control',
            'inputmode': 'numeric',
        }),
        required=False,
        label="Expiry Date"
    )
    
    card_cvv = forms.CharField(
        max_length=4,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'CVV',
            'class': 'form-control',
            'inputmode': 'numeric',
        }),
        required=False,
        label="Security Code (CVV)"
    )
    
    class Meta:
        model = Donation
        fields = ['donor_name', 'donor_email', 'interact_email', 'is_recurring', 'purpose', 'anonymous', 'payment_method']
        widgets = {
            'donor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Full Name',
            }),
            'donor_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Email Address',
            }),
            'interact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email for Interact e-Transfer receipt',
            }),
            'is_recurring': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Purpose of donation (optional)',
            }),
            'anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        donation_amount = cleaned_data.get('donation_amount')
        custom_amount = cleaned_data.get('custom_amount')
        payment_method = cleaned_data.get('payment_method')
        
        if donation_amount == 'custom':
            if not custom_amount or custom_amount <= 0:
                raise forms.ValidationError('Please enter a valid custom amount.')
        
        donor_name = cleaned_data.get('donor_name')
        anonymous = cleaned_data.get('anonymous')
        
        if not anonymous and not donor_name:
            raise forms.ValidationError('Please enter your name or check the anonymous donation checkbox.')
        
        # Validate payment method specific fields
        if payment_method == 'interact':
            if not cleaned_data.get('interact_email'):
                raise forms.ValidationError('Please provide an email for Interact e-Transfer.')
        elif payment_method == 'card':
            card_name = cleaned_data.get('card_name')
            card_number = cleaned_data.get('card_number')
            card_expiry = cleaned_data.get('card_expiry')
            card_cvv = cleaned_data.get('card_cvv')
            
            if not card_name:
                raise forms.ValidationError('Please enter the name on your card.')
            if not card_number:
                raise forms.ValidationError('Please enter your card number.')
            if not card_expiry:
                raise forms.ValidationError('Please enter the card expiry date (MM/YY).')
            if not card_cvv:
                raise forms.ValidationError('Please enter your card security code (CVV).')
            
            # Basic validation for card number (check if digits)
            card_digits = card_number.replace(' ', '')
            if not card_digits.isdigit() or len(card_digits) < 13:
                raise forms.ValidationError('Please enter a valid card number.')
        
        return cleaned_data


