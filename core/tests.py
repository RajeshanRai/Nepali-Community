from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from donations.models import Donation
from core.context_processors import site_chrome

User = get_user_model()


class SiteChromeContextProcessorTest(TestCase):
    """site_chrome must always return the required context keys."""

    REQUIRED_KEYS = [
        'top_bar_rotator_items',
        'top_bar_event_pill',
        'top_bar_donation_pill',
    ]

    def setUp(self):
        self.factory = RequestFactory()

    def _context(self):
        request = self.factory.get('/')
        return site_chrome(request)

    def test_returns_required_keys(self):
        ctx = self._context()
        for key in self.REQUIRED_KEYS:
            self.assertIn(key, ctx)

    def test_rotator_has_three_items(self):
        ctx = self._context()
        self.assertEqual(len(ctx['top_bar_rotator_items']), 3)

    def test_donation_pill_reflects_completed_donations(self):
        Donation.objects.create(
            amount=Decimal('1000.00'),
            status='completed',
            donor_email='a@example.com',
            transaction_ref='ctx-ref-1',
        )
        # Bust the cache so the processor reads fresh data
        from django.core.cache import cache
        cache.clear()

        ctx = self._context()
        self.assertIn('%', ctx['top_bar_donation_pill'])

    def test_pending_donations_not_counted(self):
        Donation.objects.create(
            amount=Decimal('50000.00'),
            status='pending',
            donor_email='b@example.com',
            transaction_ref='ctx-ref-2',
        )
        from django.core.cache import cache
        cache.clear()

        ctx = self._context()
        # Pending donations should not push the pill to "100% funded"
        self.assertNotEqual(ctx['top_bar_donation_pill'], '100% funded')
