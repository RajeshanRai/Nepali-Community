from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from donations.models import Donation

User = get_user_model()


class DonationSLAReportTest(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='staff_sla',
            password='pass123',
            email='staff_sla@example.com',
            is_staff=True,
        )

    @override_settings(DONATION_PENDING_SLA_HOURS=24)
    def test_overdue_pending_report_context(self):
        older_pending = Donation.objects.create(
            amount=Decimal('10.00'),
            status='pending',
            donor_email='old@example.com',
            transaction_ref='sla-old-1',
        )
        recent_pending = Donation.objects.create(
            amount=Decimal('15.00'),
            status='pending',
            donor_email='new@example.com',
            transaction_ref='sla-new-1',
        )
        Donation.objects.create(
            amount=Decimal('20.00'),
            status='completed',
            donor_email='done@example.com',
            transaction_ref='sla-done-1',
        )

        Donation.objects.filter(pk=older_pending.pk).update(created_at=timezone.now() - timedelta(hours=30))
        Donation.objects.filter(pk=recent_pending.pk).update(created_at=timezone.now() - timedelta(hours=3))

        self.client.login(username='staff_sla', password='pass123')
        response = self.client.get('/dashboard/donations/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pending_sla_hours'], 24)
        self.assertEqual(response.context['overdue_pending_count'], 1)
        overdue_ids = [d.pk for d in response.context['overdue_pending_donations']]
        self.assertIn(older_pending.pk, overdue_ids)
        self.assertNotIn(recent_pending.pk, overdue_ids)
