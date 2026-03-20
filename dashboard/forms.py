from django import forms
from programs.models import Program, RequestEvent
from volunteers.models import VolunteerOpportunity, VolunteerApplication
from announcements.models import Announcement
from faqs.models import FAQ, FAQCategory
from communities.models import Community
from users.models import CustomUser
from donations.models import Donation
from contacts.models import ContactMessage
from partners.models import Partner
from core.models import TeamMember


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['title', 'description', 'date', 'location', 'event_type', 'community', 'is_virtual']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Event Description'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Location'}),
            'event_type': forms.Select(attrs={'class': 'form-control'}),
            'is_virtual': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'community': forms.Select(attrs={'class': 'form-control'}),
        }


class RequestEventForm(forms.ModelForm):
    class Meta:
        model = RequestEvent
        fields = ['title', 'description', 'date', 'location', 'target_attendees', 'event_type', 'community', 'requester_name', 'requester_email', 'requester_phone']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Event Description'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
            'target_attendees': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Expected attendees'}),
            'event_type': forms.Select(attrs={'class': 'form-control'}),
            'community': forms.Select(attrs={'class': 'form-control'}),
            'requester_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
            'requester_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email'}),
            'requester_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Phone'}),
        }


class VolunteerOpportunityForm(forms.ModelForm):
    class Meta:
        model = VolunteerOpportunity
        fields = ['title', 'description', 'category', 'location', 'is_remote', 'start_date', 'end_date', 'time_commitment', 'positions_needed', 'contact_email', 'contact_phone', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opportunity Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Full Description'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
            'is_remote': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time_commitment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 5 hours/week'}),
            'positions_needed': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Contact Email'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Phone'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'category', 'priority', 'is_pinned', 'show_on_homepage', 'is_active', 'link_url', 'link_text']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Announcement Title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Announcement Content'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'link_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'External URL (optional)'}),
            'link_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Link button text (optional)'}),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_on_homepage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['question', 'answer', 'category', 'is_featured', 'is_published']
        widgets = {
            'question': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Question'}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Answer'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = [
            'user',
            'amount',
            'purpose',
            'is_recurring',
            'anonymous',
            'payment_method',
            'status',
            'donor_name',
            'donor_email',
            'interact_email',
            'card_last_four',
            'transaction_ref',
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purpose of donation'}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anonymous': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'donor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Donor name'}),
            'donor_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Donor email'}),
            'interact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e-Transfer email'}),
            'card_last_four': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '4', 'placeholder': 'Last 4 digits'}),
            'transaction_ref': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction reference'}),
        }


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message', 'attachment']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sender name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Sender email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sender phone'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Message subject'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Message body'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ['name', 'icon', 'introduction', 'member_count', 'events_per_year']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
            'icon': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'introduction': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Short introduction'}),
            'member_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'events_per_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = ['name', 'logo', 'description', 'website', 'partnership_since', 'social_links']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Partner name'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Partner description'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.org'}),
            'partnership_since': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'social_links': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '{"facebook":"https://...","twitter":"https://...","linkedin":"https://...","instagram":"https://..."}'
            }),
        }


class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ['name', 'role', 'bio', 'focus', 'badge', 'photo', 'linkedin_url', 'email', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'role': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Role or title'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Short biography'}),
            'focus': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leadership or impact focus'}),
            'badge': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Founder, Programs'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://linkedin.com/in/...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'member@example.com'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'admin@example.com'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (604) 000-0000'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = CustomUser.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This email address is already used by another account.')
        return email


class AdminPasswordForm(forms.Form):
    current_password = forms.CharField(
        label='Current password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter current password', 'autocomplete': 'current-password'}),
    )
    new_password = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Min. 8 characters', 'autocomplete': 'new-password'}),
    )
    confirm_password = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat new password', 'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data.get('current_password')
        if not self.user.check_password(password):
            raise forms.ValidationError('Current password is incorrect.')
        return password

    def clean_new_password(self):
        from django.contrib.auth.password_validation import validate_password
        password = self.cleaned_data.get('new_password')
        if password:
            validate_password(password, self.user)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', 'New passwords do not match.')
        return cleaned_data
