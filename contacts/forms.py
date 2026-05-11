from django import forms
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message', 'attachment']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your full name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'your@email.com',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '(Optional)',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Event Inquiry, Membership Question',
                'required': True
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-input textarea-input',
                'placeholder': 'Tell us more about your inquiry...',
                'rows': 5,
                'required': True
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*,.pdf,.doc,.docx'
            }),
        }
