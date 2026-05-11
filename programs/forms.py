from django import forms
from .models import Program, EventRegistration


class GuestRegistrationForm(forms.ModelForm):
    """Form for non-logged-in users to register for events"""
    class Meta:
        model = EventRegistration
        fields = ['guest_name', 'guest_email', 'guest_phone']
        widgets = {
            'guest_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name',
                'required': True
            }),
            'guest_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address',
                'required': True
            }),
            'guest_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number',
                'required': True
            }),
        }


class UserRegistrationForm(forms.ModelForm):
    """Form for logged-in users to register for events"""
    class Meta:
        model = EventRegistration
        fields = []

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)


class ProgramRegistrationForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = []  # will be set in the view


class RequestEventForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make community and date required (needed for program creation)
        self.fields['community'].required = True
        self.fields['date'].required = True
        # Always collect requester info; prefill for authenticated users
        self.fields['requester_name'].required = True
        self.fields['requester_email'].required = True
        self.fields['requester_phone'].required = False

    class Meta:
        model = __import__('programs.models', fromlist=['RequestEvent']).RequestEvent
        fields = ['title', 'description', 'location', 'date', 'event_type', 'community', 'target_attendees',
              'requester_name', 'requester_email', 'requester_phone']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event title', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Describe the event', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location/venue'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                        'event_type': forms.Select(attrs={'class': 'form-control'}),
                        'community': forms.Select(attrs={'class': 'form-control'}),
            'target_attendees': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'requester_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name', 'required': True}),
            'requester_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email', 'required': True}),
            'requester_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
        }
