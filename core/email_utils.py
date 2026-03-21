import logging
from pathlib import Path
import re
from typing import Iterable

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)
_MAIL_CSS_CACHE: str | None = None


def _clean_recipients(recipients: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for email in recipients:
        if not email:
            continue
        value = str(email).strip()
        lowered = value.lower()
        if value and lowered not in seen:
            cleaned.append(value)
            seen.add(lowered)
    return cleaned


def _load_mail_css() -> str:
    global _MAIL_CSS_CACHE
    if _MAIL_CSS_CACHE is not None:
        return _MAIL_CSS_CACHE

    css_path = Path(settings.BASE_DIR) / 'static' / 'css' / 'mail_css.css'
    try:
        _MAIL_CSS_CACHE = css_path.read_text(encoding='utf-8')
    except OSError:
        _MAIL_CSS_CACHE = ''
    return _MAIL_CSS_CACHE


def _message_to_paragraphs(message: str) -> list[str]:
    return [part.strip() for part in str(message or '').split('\n') if part.strip()]


def _recipient_name_map(recipients: list[str]) -> dict[str, str]:
    """Map recipient email -> display name using the user model."""
    lowered_recipients = {email.lower() for email in recipients}
    if not lowered_recipients:
        return {}

    UserModel = get_user_model()
    users = UserModel.objects.filter(email__in=recipients).only('email', 'username', 'first_name')

    result: dict[str, str] = {}
    for user in users:
        email = (getattr(user, 'email', '') or '').strip().lower()
        if not email or email not in lowered_recipients:
            continue
        first_name = (getattr(user, 'first_name', '') or '').strip()
        display_name = first_name or getattr(user, 'username', '') or 'Member'
        result[email] = display_name
    return result


def _personalize_html_greeting(html: str, recipient_name: str) -> str:
    if not html:
        return html

    greeting_text = f'Hello {recipient_name}, Namaste.'
    personalized = html.replace('{{username}}', recipient_name)
    personalized = personalized.replace('Hello Community Member,', greeting_text)
    personalized = personalized.replace('Hello,', greeting_text)

    # Enforce consistent greeting across all specialized templates.
    personalized = re.sub(
        r'(<p[^>]*class=["\'][^"\']*greeting[^"\']*["\'][^>]*>)(.*?)(</p>)',
        rf'\1{greeting_text}\3',
        personalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return personalized


def build_branded_email_html(
    *,
    title: str,
    greeting: str,
    intro: str,
    paragraphs: list[str] | None = None,
    highlights: list[str] | None = None,
    cta_text: str | None = None,
    cta_url: str | None = None,
    closing: str | None = None,
) -> str:
    """Render a polished branded HTML email layout."""
    return render_to_string(
        'emails/base.html',
        {
            'title': title,
            'greeting': greeting,
            'intro': intro,
            'paragraphs': paragraphs or [],
            'highlights': highlights or [],
            'cta_text': cta_text,
            'cta_url': cta_url,
            'closing': closing or 'Warm regards,\nNepali Community of Vancouver Team',
            'mail_css': _load_mail_css(),
            'brand_name': 'Nepali Community of Vancouver',
        },
    )


def render_branded_email_template(template_name: str, **context) -> str:
    """Render a branded email template with shared CSS and brand context."""
    payload = {
        'mail_css': _load_mail_css(),
        'brand_name': 'Nepali Community of Vancouver',
    }
    payload.update(context)
    return render_to_string(template_name, payload)


def build_event_newsletter_html(
    *,
    title: str,
    greeting: str,
    summary: str,
    event_name: str,
    event_date: str,
    venue_text: str,
    category_text: str,
    detail_points: list[str] | None = None,
    cta_text: str | None = None,
    cta_url: str | None = None,
) -> str:
    return render_branded_email_template(
        'emails/event_newsletter.html',
        title=title,
        greeting=greeting,
        summary=summary,
        event_name=event_name,
        event_date=event_date,
        venue_text=venue_text,
        category_text=category_text,
        detail_points=detail_points or [],
        cta_text=cta_text,
        cta_url=cta_url,
    )


def build_security_alert_html(
    *,
    title: str,
    greeting: str,
    severity_label: str,
    summary: str,
    action_items: list[str] | None = None,
    support_text: str | None = None,
    cta_text: str | None = None,
    cta_url: str | None = None,
) -> str:
    return render_branded_email_template(
        'emails/security_alert.html',
        title=title,
        greeting=greeting,
        severity_label=severity_label,
        summary=summary,
        action_items=action_items or [],
        support_text=support_text,
        cta_text=cta_text,
        cta_url=cta_url,
    )


def build_donation_receipt_html(
    *,
    title: str,
    greeting: str,
    summary: str,
    amount_text: str,
    reference_number: str,
    donation_date_text: str,
    payment_method_text: str,
    recurring_text: str,
    next_steps: list[str] | None = None,
    cta_text: str | None = None,
    cta_url: str | None = None,
) -> str:
    return render_branded_email_template(
        'emails/donation_receipt.html',
        title=title,
        greeting=greeting,
        summary=summary,
        amount_text=amount_text,
        reference_number=reference_number,
        donation_date_text=donation_date_text,
        payment_method_text=payment_method_text,
        recurring_text=recurring_text,
        next_steps=next_steps or [],
        cta_text=cta_text,
        cta_url=cta_url,
    )


def send_notification_email(
    subject: str,
    message: str,
    recipients: Iterable[str],
    html_message: str | None = None,
    send_individually: bool = True,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> bool:
    """Send notification email safely without breaking caller flows on failure."""
    recipient_list = _clean_recipients(recipients)
    if not recipient_list:
        return False

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '') or getattr(settings, 'EMAIL_HOST_USER', '')
    html_payload = html_message
    if not html_payload:
        html_payload = build_branded_email_html(
            title=subject,
            greeting='Hello {{username}}, Namaste.',
            intro='Here is an update from Nepali Community of Vancouver.',
            paragraphs=_message_to_paragraphs(message),
        )

    name_map = _recipient_name_map(recipient_list)

    try:
        if send_individually:
            # Privacy-safe default: each recipient gets a separate email and cannot see others.
            for recipient in recipient_list:
                recipient_name = name_map.get(recipient.lower(), 'Member')
                personalized_html = _personalize_html_greeting(html_payload, recipient_name)
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=message,
                    from_email=from_email,
                    to=[recipient],
                )
                email.attach_alternative(personalized_html, 'text/html')
                for attachment in attachments or []:
                    email.attach(*attachment)
                email.send(fail_silently=False)
        else:
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list,
            )
            email.attach_alternative(html_payload, 'text/html')
            for attachment in attachments or []:
                email.attach(*attachment)
            email.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.exception('Email send failed: %s', exc)
        return False
