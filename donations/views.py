from django.views.generic import FormView, TemplateView
from django.contrib import messages
from django.conf import settings
from django.db.models import Sum
from datetime import datetime
from .models import Donation
from .forms import DonationForm
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from core.email_utils import send_notification_email, build_donation_receipt_html
import uuid
from io import BytesIO
from pathlib import Path


def _resolve_receipt_logo_path():
    """Return an existing raster logo path for receipt PDFs, if available."""
    configured_logo = (getattr(settings, 'RECEIPT_LOGO_PATH', '') or '').strip()
    base_dir = Path(getattr(settings, 'BASE_DIR'))

    candidate_paths = []
    if configured_logo:
        configured_path = Path(configured_logo)
        candidate_paths.append(configured_path if configured_path.is_absolute() else base_dir / configured_path)

    candidate_paths.extend([
        base_dir / 'media' / 'community_icons' / '1.png',
        base_dir / 'media' / 'community_icons' / '1_aQasXIl.png',
        base_dir / 'media' / 'community_icons' / '1_MVQbVS7.png',
        base_dir / 'media' / 'community_icons' / '1_tW43RFy.png',
    ])

    icon_dir = base_dir / 'media' / 'community_icons'
    if icon_dir.exists():
        for ext in ('*.png', '*.jpg', '*.jpeg', '*.webp'):
            candidate_paths.extend(sorted(icon_dir.glob(ext)))

    for path in candidate_paths:
        try:
            if path.exists() and path.is_file():
                return str(path)
        except OSError:
            continue
    return None


def _build_receipt_attachment(donation, *, payment_method_text, payment_status_text):
    """Return a professional invoice-style PDF receipt attachment tuple for donor emails."""
    donor_name = donation.donor_name or 'Supporter'
    reference_number = donation.transaction_ref or str(donation.pk)
    filename_base = f'donation-receipt-{reference_number}'
    issue_date = donation.created_at.strftime('%B %d, %Y')
    due_date = issue_date
    business_name = getattr(settings, 'COMMUNITY_NAME', 'Nepali Community of Vancouver')
    donation_amount = f'${donation.amount:,.2f}'
    normalized_status = (payment_status_text or '').strip().lower()
    status_label = 'Paid' if normalized_status in {'paid', 'completed', 'succeeded'} else 'Unpaid'
    invoice_number = f'INV-{donation.pk:05d}'
    payment_link = getattr(settings, 'SITE_URL', '').strip()
    donor_address_parts = [
        (donation.donor_address_line1 or '').strip(),
        (donation.donor_city or '').strip(),
        (donation.donor_province or '').strip(),
        (donation.donor_postal_code or '').strip(),
    ]
    donor_address = ', '.join(part for part in donor_address_parts if part)

    # Fallback text receipt remains available in case PDF rendering fails.
    fallback_lines = [
        'Nepali Community of Vancouver',
        'Donation Receipt',
        '',
        f'Donor: {donor_name}',
        f'Donor Email: {donation.donor_email or "-"}',
        f'Donor Phone: {donation.donor_phone or "-"}',
        f'Donor Address: {donor_address or "-"}',
        f'Amount: ${donation.amount}',
        f'Reference Number: {reference_number}',
        f'Date: {donation.created_at.strftime("%B %d, %Y %I:%M %p")}',
        f'Payment Method: {payment_method_text}',
        f'Recurring: {"Yes" if donation.is_recurring else "No"}',
        f'Payment Status: {payment_status_text}',
    ]
    if donation.card_last_four:
        fallback_lines.append(f'Card Last 4: **** {donation.card_last_four}')
    if donation.stripe_payment_intent_id:
        fallback_lines.append(f'Stripe Payment Intent: {donation.stripe_payment_intent_id}')
    fallback_lines.append('')
    fallback_lines.append('Thank you for supporting the Nepali Community of Vancouver.')

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.enums import TA_RIGHT
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            rightMargin=0.65 * inch,
            leftMargin=0.65 * inch,
            topMargin=0.65 * inch,
            bottomMargin=0.65 * inch,
            title='Donation Invoice',
            author=business_name,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=26,
            leading=28,
            textColor=colors.HexColor('#1F2937'),
            alignment=TA_RIGHT,
        )
        company_style = ParagraphStyle(
            'CompanyName',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=16,
            textColor=colors.HexColor('#111827'),
        )
        tagline_style = ParagraphStyle(
            'Tagline',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#6B7280'),
        )
        section_heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=colors.HexColor('#4B5563'),
            spaceAfter=5,
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#1F2937'),
        )
        muted_style = ParagraphStyle(
            'Muted',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#6B7280'),
        )
        memo_style = ParagraphStyle(
            'Memo',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#4B5563'),
        )
        right_body_style = ParagraphStyle(
            'RightBody',
            parent=body_style,
            alignment=TA_RIGHT,
        )

        accent = colors.HexColor('#0EA5A4')
        elements = []

        logo_path = _resolve_receipt_logo_path()
        if logo_path:
            logo_element = Image(logo_path, width=0.62 * inch, height=0.62 * inch)
            logo_element.hAlign = 'LEFT'
            company_block = Table(
                [[logo_element, Paragraph(f'<b>{business_name}</b>', company_style)], [
                    '',
                    Paragraph('Supporting a collaborative community platform', tagline_style),
                ]],
                colWidths=[0.75 * inch, 3.70 * inch],
            )
            company_block.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('SPAN', (0, 1), (0, 1)),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            left_header = company_block
        else:
            left_header = Table(
                [[Paragraph(f'<b>{business_name}</b>', company_style)], [
                    Paragraph('Supporting a collaborative community platform', tagline_style),
                ]],
                colWidths=[4.45 * inch],
            )
            left_header.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))

        header_table = Table(
            [[
                left_header,
                Paragraph('INVOICE', title_style),
            ]],
            colWidths=[4.45 * inch, 2.35 * inch],
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, 0), 0.6, colors.HexColor('#E5E7EB')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.20 * inch))

        details_rows = [
            ['Invoice Number', invoice_number],
            ['Issue Date', issue_date],
            ['Due Date', due_date],
            ['Status', status_label],
        ]
        details_table = Table(details_rows, colWidths=[1.2 * inch, 1.15 * inch])
        details_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4B5563')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#111827')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#E5E7EB')),
            ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E5E7EB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        bill_to_lines = [
            Paragraph('BILL TO', section_heading_style),
            Paragraph(donor_name, body_style),
            Paragraph(donation.donor_email or 'No email provided', body_style),
        ]
        if donation.donor_phone:
            bill_to_lines.append(Paragraph(donation.donor_phone, body_style))
        if donor_address:
            bill_to_lines.append(Paragraph(donor_address, body_style))

        top_info_table = Table(
            [[bill_to_lines, details_table]],
            colWidths=[4.45 * inch, 2.35 * inch],
        )
        top_info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, 0), 0.6, colors.HexColor('#E5E7EB')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(top_info_table)
        elements.append(Spacer(1, 0.18 * inch))

        description_text = (
            'Community website donation (supporting hosting, maintenance, and development)'
        )
        description_cell = Paragraph(description_text, body_style)

        invoice_table = Table(
            [[
                'Description',
                'Quantity',
                'Unit Price',
                'Total',
            ], [
                description_cell,
                '1',
                donation_amount,
                donation_amount,
            ]],
            colWidths=[4.0 * inch, 0.9 * inch, 1.0 * inch, 0.9 * inch],
        )
        invoice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9.5),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#111827')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#E5E7EB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(invoice_table)
        elements.append(Spacer(1, 0.16 * inch))

        summary_table = Table(
            [
                ['', 'Subtotal:', donation_amount],
                ['', 'Total:', donation_amount],
            ],
            colWidths=[4.45 * inch, 1.2 * inch, 1.15 * inch],
        )
        summary_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONT', (1, 0), (1, 0), 'Helvetica', 10),
            ('FONT', (2, 0), (2, 0), 'Helvetica', 10),
            ('FONT', (1, 1), (1, 1), 'Helvetica-Bold', 11),
            ('FONT', (2, 1), (2, 1), 'Helvetica-Bold', 12),
            ('TEXTCOLOR', (1, 0), (-1, -1), colors.HexColor('#111827')),
            ('LINEABOVE', (1, 1), (2, 1), 0.9, colors.HexColor('#D1D5DB')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.18 * inch))

        payment_lines = [
            Paragraph('PAYMENT INFORMATION', section_heading_style),
            Paragraph(f'Payment Method: {payment_method_text}', body_style),
        ]
        if payment_link:
            payment_lines.append(Paragraph(f'Payment Link: {payment_link}', body_style))
        if donation.stripe_payment_intent_id:
            payment_lines.append(Paragraph(f'Stripe Payment Intent: {donation.stripe_payment_intent_id}', body_style))
        if donation.card_last_four:
            payment_lines.append(Paragraph(f'Card Last 4: **** {donation.card_last_four}', body_style))
        for line in payment_lines:
            elements.append(line)

        elements.append(Spacer(1, 0.14 * inch))
        memo_text = (
            'Thank you for your donation. Your support helps us maintain and grow '
            'our community website for everyone.'
        )
        memo_box = Table([[Paragraph(memo_text, memo_style)]], colWidths=[6.8 * inch])
        memo_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (0, 0), 0.6, colors.HexColor('#E5E7EB')),
            ('LEFTPADDING', (0, 0), (0, 0), 9),
            ('RIGHTPADDING', (0, 0), (0, 0), 9),
            ('TOPPADDING', (0, 0), (0, 0), 8),
            ('BOTTOMPADDING', (0, 0), (0, 0), 8),
        ]))
        elements.append(memo_box)
        elements.append(Spacer(1, 0.2 * inch))

        footer_rows = [
            [Paragraph('Thank you for your support. This contribution helps sustain and grow our community platform.', muted_style)],
            [Paragraph('This invoice represents a voluntary donation. No goods or services were exchanged.', muted_style)],
            [Paragraph('Please keep this invoice for your records.', muted_style)],
        ]
        footer_table = Table(footer_rows, colWidths=[6.8 * inch])
        footer_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (0, 0), 0.7, accent),
            ('TOPPADDING', (0, 0), (0, -1), 5),
            ('BOTTOMPADDING', (0, 0), (0, -1), 2),
        ]))
        elements.append(footer_table)

        doc.build(elements)

        pdf_content = buffer.getvalue()
        buffer.close()
        return (f'{filename_base}.pdf', pdf_content, 'application/pdf')
    except Exception:
        return (f'{filename_base}.txt', '\n'.join(fallback_lines).encode('utf-8'), 'text/plain')


def _get_stripe_client():
    """Return configured stripe module or an error message."""
    try:
        import stripe
    except ImportError:
        return None, 'Stripe SDK is not installed. Run: pip install stripe'

    public_key = (getattr(settings, 'STRIPE_PUBLIC_KEY', '') or '').strip()
    secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()

    if (
        not public_key
        or not secret_key
        or 'xxx' in public_key.lower()
        or 'xxx' in secret_key.lower()
    ):
        return None, 'Stripe is not configured. Replace STRIPE_PUBLIC_KEY and STRIPE_SECRET_KEY in .env with real Stripe test keys.'

    stripe.api_key = secret_key
    return stripe, None


def _is_stripe_test_mode_active():
    """True only when real Stripe test keys are loaded."""
    public_key = (getattr(settings, 'STRIPE_PUBLIC_KEY', '') or '').strip()
    secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    return (
        public_key.startswith('pk_test_')
        and secret_key.startswith('sk_test_')
        and 'xxx' not in public_key.lower()
        and 'xxx' not in secret_key.lower()
    )


def _extract_card_last4(stripe, payment_intent_id):
    """Best-effort extraction of card last4 from Stripe PaymentIntent."""
    if not payment_intent_id:
        return ''

    try:
        payment_intent = stripe.PaymentIntent.retrieve(
            payment_intent_id,
            expand=['latest_charge.payment_method_details']
        )
        latest_charge = payment_intent.get('latest_charge')

        if isinstance(latest_charge, dict):
            card = (latest_charge.get('payment_method_details') or {}).get('card') or {}
            last4 = (card.get('last4') or '').strip()
            return last4[:4]
    except Exception:
        return ''

    return ''


class DonationView(FormView):
    template_name = 'donations/donate.html'
    form_class = DonationForm
    success_url = reverse_lazy('payment_success')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['donation_stats'] = self.get_donation_statistics()
        context['stripe_test_mode_active'] = _is_stripe_test_mode_active()
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
        
        donation.save()

        if payment_method == 'card':
            checkout_session, error_message = self.create_stripe_checkout_session(donation)
            if error_message:
                donation.delete()
                form.add_error(None, error_message)
                messages.error(self.request, error_message)
                return self.form_invalid(form)

            donation.stripe_session_id = checkout_session.id
            donation.save(update_fields=['stripe_session_id'])

            self.request.session['donation_id'] = donation.id
            self.request.session['donation_amount'] = str(donation.amount)
            self.request.session['payment_method'] = payment_method
            return redirect(checkout_session.url)
        
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

    def create_stripe_checkout_session(self, donation):
        stripe, error_message = _get_stripe_client()
        if error_message:
            return None, error_message

        amount_cents = int(round(float(donation.amount) * 100))
        if amount_cents <= 0:
            return None, 'Donation amount must be greater than zero.'

        success_url = self.request.build_absolute_uri(reverse_lazy('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = self.request.build_absolute_uri(reverse_lazy('payment_cancel'))
        donation_label = donation.purpose.strip() if donation.purpose else 'Nepali Community Donation'

        line_item = {
            'price_data': {
                'currency': 'cad',
                'unit_amount': amount_cents,
                'product_data': {
                    'name': donation_label,
                },
            },
            'quantity': 1,
        }
        if donation.is_recurring:
            line_item['price_data']['recurring'] = {'interval': 'month'}

        session_kwargs = {
            'mode': 'subscription' if donation.is_recurring else 'payment',
            'payment_method_types': ['card'],
            'line_items': [line_item],
            'success_url': success_url,
            'cancel_url': cancel_url,
            'metadata': {
                'donation_id': str(donation.id),
                'transaction_ref': donation.transaction_ref,
            },
        }

        if donation.donor_email:
            session_kwargs['customer_email'] = donation.donor_email

        try:
            session = stripe.checkout.Session.create(**session_kwargs)
            return session, None
        except Exception as exc:
            return None, f'Unable to start Stripe checkout: {exc}'

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
                attachments=[
                    _build_receipt_attachment(
                        donation,
                        payment_method_text='Interac e-Transfer' if payment_method == 'interact' else 'Credit/Debit Card',
                        payment_status_text='Pending confirmation' if payment_method == 'interact' else 'Processing',
                    )
                ],
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
        context['payment_status'] = 'pending'

        stripe_session_id = self.request.GET.get('session_id')
        if stripe_session_id:
            stripe, error_message = _get_stripe_client()
            if not error_message:
                try:
                    stripe_session = stripe.checkout.Session.retrieve(stripe_session_id)
                    donation = Donation.objects.filter(stripe_session_id=stripe_session_id).first()

                    if donation:
                        context['donation_amount'] = str(donation.amount)
                        context['payment_method'] = donation.payment_method
                        was_marked_completed = False

                        payment_intent_id = stripe_session.payment_intent or donation.stripe_payment_intent_id
                        update_fields = []

                        if payment_intent_id and donation.stripe_payment_intent_id != payment_intent_id:
                            donation.stripe_payment_intent_id = payment_intent_id
                            update_fields.append('stripe_payment_intent_id')

                        last4 = _extract_card_last4(stripe, payment_intent_id)
                        if last4 and donation.card_last_four != last4:
                            donation.card_last_four = last4
                            update_fields.append('card_last_four')

                        if stripe_session.payment_status == 'paid' and donation.status != 'completed':
                            donation.status = 'completed'
                            update_fields.append('status')
                            was_marked_completed = True

                        if update_fields:
                            donation.save(update_fields=sorted(set(update_fields)))

                        if was_marked_completed:
                            self.send_confirmation_email(donation)

                        if donation.status == 'completed':
                            context['payment_status'] = 'completed'
                except Exception:
                    pass
        return context

    def send_confirmation_email(self, donation):
        """Send receipt after Stripe confirms payment."""
        subject = f'Donation Confirmation - ${donation.amount}'
        recipient_email = donation.donor_email
        if not recipient_email:
            return

        message = f"""
Thank you for your generous donation!

=== DONATION DETAILS ===
Amount: ${donation.amount}
Reference #: {donation.transaction_ref}
Date: {donation.created_at.strftime('%B %d, %Y')}
Recurring: {'Yes' if donation.is_recurring else 'No'}
Payment Method: Credit/Debit Card (Stripe)

=== PAYMENT STATUS ===
Your card payment has been completed successfully.

We appreciate your support of the Nepali Community of Vancouver!

Best regards,
Nepali Community of Vancouver Team
        """
        html_message = build_donation_receipt_html(
            title='Donation Completed Successfully',
            greeting=f"Hi {donation.donor_name or 'Supporter'},",
            summary='Thank you for your contribution. Your Stripe payment has been confirmed.',
            amount_text=f"${donation.amount}",
            reference_number=donation.transaction_ref,
            donation_date_text=donation.created_at.strftime('%B %d, %Y'),
            payment_method_text='Credit/Debit Card (Stripe)',
            recurring_text='Yes' if donation.is_recurring else 'No',
            next_steps=[
                'Please keep this receipt for your records.',
                'If you selected recurring, future monthly charges will continue until cancelled.',
            ],
        )

        try:
            send_notification_email(
                subject=subject,
                message=message,
                recipients=[recipient_email],
                html_message=html_message,
                attachments=[
                    _build_receipt_attachment(
                        donation,
                        payment_method_text='Credit/Debit Card (Stripe)',
                        payment_status_text='Completed',
                    )
                ],
            )
        except Exception:
            pass


class PaymentCancelView(TemplateView):
    template_name = 'donations/cancel.html'


class DonationStatsAPIView(TemplateView):
    """API endpoint for real-time donation statistics (JSON)"""
    
    def get(self, request, *args, **kwargs):
        # Reuse the statistics calculation logic from DonationView
        donation_view = DonationView()
        stats = donation_view.get_donation_statistics()
        
        return JsonResponse(stats)


@csrf_exempt
def stripe_webhook(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')

    stripe, error_message = _get_stripe_client()
    if error_message:
        return HttpResponse(error_message, status=503)

    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponseBadRequest('Missing STRIPE_WEBHOOK_SECRET')

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return HttpResponseBadRequest('Invalid payload')
    except stripe.error.SignatureVerificationError:
        return HttpResponseBadRequest('Invalid signature')

    event_type = event.get('type')

    if event_type == 'checkout.session.completed':
        session = event['data']['object']
        donation = Donation.objects.filter(stripe_session_id=session.get('id')).first()
        if donation:
            update_fields = []
            payment_intent_id = session.get('payment_intent', '') or donation.stripe_payment_intent_id

            if payment_intent_id and donation.stripe_payment_intent_id != payment_intent_id:
                donation.stripe_payment_intent_id = payment_intent_id
                update_fields.append('stripe_payment_intent_id')

            last4 = _extract_card_last4(stripe, payment_intent_id)
            if last4 and donation.card_last_four != last4:
                donation.card_last_four = last4
                update_fields.append('card_last_four')

            if donation.status != 'completed':
                donation.status = 'completed'
                update_fields.append('status')

            if update_fields:
                donation.save(update_fields=sorted(set(update_fields)))

            if 'status' in update_fields and donation.status == 'completed' and donation.donor_email:
                PaymentSuccessView().send_confirmation_email(donation)

    if event_type == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        donation = Donation.objects.filter(stripe_payment_intent_id=payment_intent.get('id')).first()
        if donation:
            donation.status = 'failed'
            donation.save(update_fields=['status'])

    return HttpResponse(status=200)

