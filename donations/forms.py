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
        min_value=1,
        max_value=100000,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Enter custom amount',
            'class': 'form-control',
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
    
    class Meta:
        model = Donation
        fields = [
            'donor_name',
            'donor_email',
            'donor_phone',
            'donor_address_line1',
            'donor_city',
            'donor_province',
            'donor_postal_code',
            'interact_email',
            'is_recurring',
            'purpose',
            'anonymous',
            'payment_method',
        ]
        widgets = {
            'donor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Full Name',
            }),
            'donor_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Email Address',
            }),
            'donor_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number (optional)',
            }),
            'donor_address_line1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street Address (optional)',
            }),
            'donor_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City (optional)',
            }),
            'donor_province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Province/State (optional)',
            }),
            'donor_postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postal Code (optional)',
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
        
        return cleaned_data


