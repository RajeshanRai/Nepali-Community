from django.views.generic import FormView, TemplateView
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Donation
from .forms import DonationForm
from django.urls import reverse_lazy
from core.email_utils import send_notification_email, build_donation_receipt_html
import uuid
import json


class DonationView(FormView):
    template_name = 'donations/donate.html'
    form_class = DonationForm
    success_url = reverse_lazy('payment_success')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['donation_stats'] = self.get_donation_statistics()
        return context

    def get_donation_statistics(self):
        """Calculate real-time donation statistics"""
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Get all completed donations
        all_donations = Donation.objects.filter(status='completed')
        year_donations = all_donations.filter(created_at__year=current_year)
        month_donations = all_donations.filter(
            created_at__year=current_year,
            created_at__month=current_month
        )
        
        # Calculate statistics
        total_raised = year_donations.aggregate(Sum('amount'))['amount__sum'] or 0
        total_donors = all_donations.values('donor_email').distinct().count()
        donors_this_month = month_donations.values('donor_email').distinct().count()
        
        # Calculate monthly average
        months_with_donations = year_donations.values('created_at__month').distinct().count()
        monthly_average = float(total_raised) / months_with_donations if months_with_donations > 0 else 0
        
        # Annual goal
        annual_goal = 60000
        goal_percentage = min(100, round((float(total_raised) / annual_goal) * 100))
        amount_remaining = max(0, annual_goal - float(total_raised))
        
        return {
            'total_raised': float(total_raised),
            'total_raised_formatted': f"{total_raised:,.2f}",
            'total_donors': total_donors,
            'donors_this_month': donors_this_month,
            'monthly_average': float(monthly_average),
            'monthly_average_formatted': f"{monthly_average:,.2f}",
            'goal_percentage': int(goal_percentage),
            'annual_goal': annual_goal,
            'annual_goal_formatted': f"{annual_goal:,.2f}",
            'amount_raised': float(total_raised),
            'amount_raised_formatted': f"{total_raised:,.2f}",
            'amount_remaining': float(amount_remaining),
            'amount_remaining_formatted': f"{amount_remaining:,.2f}",
        }

    def form_valid(self, form):
        # Extract form data
        donation_amount = form.cleaned_data.get('donation_amount')
        custom_amount = form.cleaned_data.get('custom_amount')
        payment_method = form.cleaned_data.get('payment_method')
        
        # Determine final amount
        if donation_amount == 'custom':
            amount = custom_amount
        else:
            amount = donation_amount
        
        # Create donation instance
        donation = form.save(commit=False)
        donation.amount = amount
        donation.payment_method = payment_method
        donation.transaction_ref = str(uuid.uuid4())
        
        # Set user if authenticated
        if self.request.user.is_authenticated:
            donation.user = self.request.user
            if not donation.donor_name:
                donation.donor_name = self.request.user.get_full_name() or self.request.user.username
            if not donation.donor_email:
                donation.donor_email = self.request.user.email
        
        # Store last 4 digits of card if payment method is card
        if payment_method == 'card':
            card_number = form.cleaned_data.get('card_number', '')
            # Extract last 4 digits (remove spaces first)
            card_digits = card_number.replace(' ', '')
            if len(card_digits) >= 4:
                donation.card_last_four = card_digits[-4:]
        
        donation.save()
        
        # Send confirmation email
        self.send_confirmation_email(donation, form.cleaned_data)
        
        # Store donation info in session for success page
        self.request.session['donation_id'] = donation.id
        self.request.session['donation_amount'] = str(donation.amount)
        self.request.session['payment_method'] = payment_method
        
        if payment_method == 'interact':
            self.request.session['interact_email'] = donation.interact_email
        
        messages.success(self.request, f'Thank you! Your donation of ${donation.amount} is being processed.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the donation form errors and try again.')
        return super().form_invalid(form)
    
    def send_confirmation_email(self, donation, cleaned_data):
        """Send confirmation email with payment details"""
        subject = f'Donation Confirmation - ${donation.amount}'
        recipient_email = donation.donor_email or donation.interact_email
        if not recipient_email:
            return
        
        payment_method = donation.payment_method
        
        if payment_method == 'interact':
            message = f"""
Thank you for your generous donation!

=== DONATION DETAILS ===
Amount: ${donation.amount}
Reference #: {donation.transaction_ref}
Date: {donation.created_at.strftime('%B %d, %Y')}
Recurring: {'Yes' if donation.is_recurring else 'No'}
Payment Method: Interact e-Transfer

=== NEXT STEPS ===
Please send an Interact e-Transfer to: donations@nepalicommunityvancouver.ca

Amount: ${donation.amount}
Reference: Use your Reference # {donation.transaction_ref} in the transfer message
Your email for the transfer: {donation.interact_email}

Once we receive your e-Transfer, we will confirm your donation.

Thank you for supporting the Nepali Community of Vancouver!

Best regards,
Nepali Community of Vancouver Team
            """
            html_message = build_donation_receipt_html(
                title='Donation Initiated Successfully',
                greeting=f"Hi {donation.donor_name or 'Supporter'},",
                summary='Thank you for beginning your contribution. Your receipt details are below.',
                amount_text=f"${donation.amount}",
                reference_number=donation.transaction_ref,
                donation_date_text=donation.created_at.strftime('%B %d, %Y'),
                payment_method_text='Interact e-Transfer',
                recurring_text='Yes' if donation.is_recurring else 'No',
                next_steps=[
                    'Send your transfer to donations@nepalicommunityvancouver.ca.',
                    f'Include reference {donation.transaction_ref} in your transfer note.',
                    'You will receive a confirmation as soon as payment is verified.',
                ],
            )
        else:  # card payment
            message = f"""
Thank you for your generous donation!

=== DONATION DETAILS ===
Amount: ${donation.amount}
Reference #: {donation.transaction_ref}
Date: {donation.created_at.strftime('%B %d, %Y')}
Recurring: {'Yes' if donation.is_recurring else 'No'}
Payment Method: Credit/Debit Card

=== PAYMENT STATUS ===
Your card payment is being processed. You will receive a confirmation email within 24 hours once the payment is complete.

We appreciate your support of the Nepali Community of Vancouver!

Best regards,
Nepali Community of Vancouver Team
            """
            html_message = build_donation_receipt_html(
                title='Donation Confirmation Received',
                greeting=f"Hi {donation.donor_name or 'Supporter'},",
                summary='Your contribution has been received and is currently being processed.',
                amount_text=f"${donation.amount}",
                reference_number=donation.transaction_ref,
                donation_date_text=donation.created_at.strftime('%B %d, %Y'),
                payment_method_text='Credit/Debit Card',
                recurring_text='Yes' if donation.is_recurring else 'No',
                next_steps=[
                    'You will receive final card processing confirmation within 24 hours.',
                    'Please keep this receipt reference for your records.',
                ],
            )
        
        try:
            send_notification_email(
                subject=subject,
                message=message,
                recipients=[recipient_email],
                html_message=html_message,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending donation confirmation email to {recipient_email}: {e}")


class PaymentSuccessView(TemplateView):
    template_name = 'donations/success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['donation_amount'] = self.request.session.get('donation_amount', '0')
        context['interact_email'] = self.request.session.get('interact_email', '')
        context['payment_method'] = self.request.session.get('payment_method', 'interact')
        return context


class PaymentCancelView(TemplateView):
    template_name = 'donations/cancel.html'


class DonationStatsAPIView(TemplateView):
    """API endpoint for real-time donation statistics (JSON)"""
    
    def get(self, request, *args, **kwargs):
        from django.http import JsonResponse
        
        # Reuse the statistics calculation logic from DonationView
        donation_view = DonationView()
        stats = donation_view.get_donation_statistics()
        
        return JsonResponse(stats)

