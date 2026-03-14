from django import forms
from .models import VolunteerApplication, VolunteerRequest


class VolunteerApplicationForm(forms.ModelForm):
    class Meta:
        model = VolunteerApplication
        fields = ['name', 'email', 'phone', 'motivation', 'experience', 'availability']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number (optional)'
            }),
            'motivation': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Why do you want to volunteer for this opportunity?',
                'rows': 4,
                'required': True
            }),
            'experience': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Any relevant experience or skills? (optional)',
                'rows': 3
            }),
            'availability': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'When are you available? (days/times)',
                'rows': 3
            }),
        }
        labels = {
            'name': 'Your Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'motivation': 'Why do you want to volunteer?',
            'experience': 'Relevant Experience',
            'availability': 'Your Availability',
        }


class VolunteerRequestForm(forms.ModelForm):
    class Meta:
        model = VolunteerRequest
        fields = [
            'name',
            'phone',
            'email',
            'address',
            'volunteer_type',
            'expertise',
            'schedule_availability',
            'purpose',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current Address'}),
            'volunteer_type': forms.Select(attrs={'class': 'form-control'}),
            'expertise': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Expertise (e.g., teaching, medical, IT)'
            }),
            'schedule_availability': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Weekends, Evenings, Mondays 6-8 PM'
            }),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Why do you want to volunteer?'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        volunteer_type = cleaned_data.get('volunteer_type')
        expertise = (cleaned_data.get('expertise') or '').strip()

        if volunteer_type == 'expertise' and not expertise:
            self.add_error('expertise', 'Please provide your expertise for expertise-based volunteering.')

        return cleaned_data
