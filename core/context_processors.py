from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from announcements.models import Announcement
from donations.models import Donation
from programs.models import Program


ANNUAL_DONATION_GOAL = Decimal('60000.00')


def site_chrome(request):
    now = timezone.now()
    today = timezone.localdate()

    upcoming_count = Program.objects.filter(date__gte=today).count()

    latest_announcement = (
        Announcement.objects.filter(
            is_active=True,
            publish_date__lte=now,
        )
        .filter(Q(expire_date__isnull=True) | Q(expire_date__gt=now))
        .order_by('-is_pinned', '-publish_date')
        .only('title', 'priority')
        .first()
    )

    annual_total = (
        Donation.objects.filter(
            status='completed',
            created_at__year=now.year,
        ).aggregate(total=Sum('amount'))['total']
        or Decimal('0')
    )

    donation_progress = 0
    if ANNUAL_DONATION_GOAL > 0:
        donation_progress = min(100, int((annual_total / ANNUAL_DONATION_GOAL) * 100))

    rotator_items = [
        {
            'kicker': 'Events',
            'text': (
                f'{upcoming_count} upcoming program'
                f'{'s' if upcoming_count != 1 else ''} '
                'open for the community calendar.'
            ) if upcoming_count else 'New community events are being prepared for the calendar.',
        },
        {
            'kicker': 'Giving',
            'text': f'${annual_total:,.0f} raised toward the ${ANNUAL_DONATION_GOAL:,.0f} annual community goal.',
        },
        {
            'kicker': 'Announcement',
            'text': latest_announcement.title if latest_announcement else 'Fresh announcements will appear here as soon as they are published.',
        },
    ]

    return {
        'top_bar_rotator_items': rotator_items,
        'top_bar_event_pill': f'{upcoming_count} upcoming' if upcoming_count else 'Calendar warming up',
        'top_bar_donation_pill': f'{donation_progress}% funded' if donation_progress else 'Donations open',
    }