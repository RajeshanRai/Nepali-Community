from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from .forms import DonationForm
from .models import Donation, StripeWebhookEvent
from .views import DonationView, stripe_webhook, _get_stripe_key_mode

User = get_user_model()


# ---------------------------------------------------------------------------
# DonationForm validation
# ---------------------------------------------------------------------------

class DonationFormValidationTest(TestCase):
    """Test server-side validation on the donation form."""

    BASE_DATA = {
        'donation_amount': '20',
        'payment_method': 'interact',
        'donor_name': 'Test Donor',
        'donor_email': 'donor@example.com',
        'interact_email': 'donor@example.com',
        'is_recurring': False,
        'anonymous': False,
    }

    def _form(self, overrides=None):
        data = {**self.BASE_DATA, **(overrides or {})}
        return DonationForm(data=data)

    # --- preset tiers ---

    def test_valid_preset_tier(self):
        form = self._form({'donation_amount': '50'})
        self.assertTrue(form.is_valid(), form.errors)

    # --- custom amount ---

    def test_valid_custom_amount(self):
        form = self._form({'donation_amount': 'custom', 'custom_amount': '75.00'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_custom_amount_zero_is_invalid(self):
        form = self._form({'donation_amount': 'custom', 'custom_amount': '0'})
        self.assertFalse(form.is_valid())

    def test_custom_amount_negative_is_invalid(self):
        form = self._form({'donation_amount': 'custom', 'custom_amount': '-10'})
        self.assertFalse(form.is_valid())

    def test_custom_amount_exceeds_max_is_invalid(self):
        form = self._form({'donation_amount': 'custom', 'custom_amount': '200000'})
        self.assertFalse(form.is_valid())

    def test_custom_amount_missing_raises_error(self):
        form = self._form({'donation_amount': 'custom', 'custom_amount': ''})
        self.assertFalse(form.is_valid())

    # --- anonymous / name ---

    def test_anonymous_does_not_require_name(self):
        form = self._form({'donor_name': '', 'anonymous': True})
        self.assertTrue(form.is_valid(), form.errors)

    def test_non_anonymous_requires_name(self):
        form = self._form({'donor_name': '', 'anonymous': False})
        self.assertFalse(form.is_valid())

    # --- interact email ---

    def test_interact_requires_interact_email(self):
        form = self._form({'payment_method': 'interact', 'interact_email': ''})
        self.assertFalse(form.is_valid())

    def test_card_payment_does_not_require_interact_email(self):
        form = self._form({'payment_method': 'card', 'interact_email': ''})
        self.assertTrue(form.is_valid(), form.errors)


# ---------------------------------------------------------------------------
# DonationView – form_valid backend amount bounds
# ---------------------------------------------------------------------------

class DonationViewAmountBoundsTest(TestCase):
    """Verify the view rejects out-of-range amounts even if form passes."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser', password='pass', email='u@example.com'
        )

    def _post(self, post_data):
        request = self.factory.post('/donate/', post_data)
        request.user = self.user
        request.session = {}
        return request

    def test_amount_below_minimum_rejected(self):
        """Manually manipulated amount below $1 must fail in form_valid."""
        # custom_amount below minimum bypasses form field (min_value=1) only if
        # submitted raw; test that view also enforces the bound.
        response = self.client.post(reverse('donation'), {
            'donation_amount': 'custom',
            'custom_amount': '0.50',
            'payment_method': 'interact',
            'donor_name': 'Test',
            'donor_email': 'test@example.com',
            'interact_email': 'test@example.com',
            'anonymous': False,
        })
        # Should not redirect to success; expect form re-render (200) or redirect to same page
        self.assertNotEqual(response.status_code, 302, "Out-of-bounds amount should not succeed")

    def test_very_large_amount_rejected(self):
        response = self.client.post(reverse('donation'), {
            'donation_amount': 'custom',
            'custom_amount': '999999',
            'payment_method': 'interact',
            'donor_name': 'Test',
            'donor_email': 'test@example.com',
            'interact_email': 'test@example.com',
            'anonymous': False,
        })
        self.assertNotEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# Donation model
# ---------------------------------------------------------------------------

class DonationModelTest(TestCase):

    def test_str_anonymous(self):
        d = Donation(amount=Decimal('25.00'), anonymous=True)
        self.assertIn('Anonymous', str(d))

    def test_str_named(self):
        d = Donation(amount=Decimal('50.00'), anonymous=False, donor_name='Alice')
        self.assertIn('Alice', str(d))

    def test_default_status_is_pending(self):
        d = Donation(amount=Decimal('10.00'))
        self.assertEqual(d.status, 'pending')


# ---------------------------------------------------------------------------
# DonationView.get_donation_statistics
# ---------------------------------------------------------------------------

class DonationStatisticsTest(TestCase):
    """Test the statistics calculation method."""

    def setUp(self):
        # Create completed and pending donations
        Donation.objects.create(
            amount=Decimal('100.00'),
            status='completed',
            donor_email='a@example.com',
            transaction_ref='ref-a',
        )
        Donation.objects.create(
            amount=Decimal('50.00'),
            status='completed',
            donor_email='b@example.com',
            transaction_ref='ref-b',
        )
        Donation.objects.create(
            amount=Decimal('200.00'),
            status='pending',
            donor_email='c@example.com',
            transaction_ref='ref-c',
        )

    def _stats(self):
        view = DonationView()
        return view.get_donation_statistics()

    def test_total_raised_excludes_pending(self):
        stats = self._stats()
        self.assertEqual(stats['total_raised'], 150.0)

    def test_goal_percentage_is_sensible(self):
        stats = self._stats()
        self.assertGreaterEqual(stats['goal_percentage'], 0)
        self.assertLessEqual(stats['goal_percentage'], 100)

    def test_total_donors_counts_unique_emails(self):
        stats = self._stats()
        self.assertEqual(stats['total_donors'], 2)

    def test_amount_remaining_is_non_negative(self):
        stats = self._stats()
        self.assertGreaterEqual(stats['amount_remaining'], 0)


class StripeKeyModeValidationTest(TestCase):

    def test_accepts_test_mode_pair(self):
        mode, error = _get_stripe_key_mode('pk_test_123', 'sk_test_456')
        self.assertEqual(mode, 'test')
        self.assertIsNone(error)

    def test_accepts_live_mode_pair(self):
        mode, error = _get_stripe_key_mode('pk_live_123', 'sk_live_456')
        self.assertEqual(mode, 'live')
        self.assertIsNone(error)

    def test_rejects_mixed_modes(self):
        mode, error = _get_stripe_key_mode('pk_test_123', 'sk_live_456')
        self.assertIsNone(mode)
        self.assertIn('mismatch', error.lower())


class StripeWebhookHardeningTest(TestCase):

    def _make_donation(self):
        return Donation.objects.create(
            amount=Decimal('55.00'),
            status='pending',
            donor_email='stripe@example.com',
            transaction_ref='txn-webhook-001',
            stripe_session_id='cs_test_123',
            payment_method='card',
        )

    def _event_for(self, donation, *, event_id='evt_001', metadata_donation_id=None, metadata_ref=None):
        return {
            'id': event_id,
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': donation.stripe_session_id,
                    'payment_intent': 'pi_test_123',
                    'metadata': {
                        'donation_id': metadata_donation_id if metadata_donation_id is not None else str(donation.pk),
                        'transaction_ref': metadata_ref if metadata_ref is not None else donation.transaction_ref,
                    },
                }
            },
        }

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('donations.views.PaymentSuccessView.send_confirmation_email')
    @patch('donations.views._extract_card_last4', return_value='4242')
    @patch('donations.views._get_stripe_client')
    def test_duplicate_webhook_event_is_ignored(self, mock_client, _mock_last4, mock_send_email):
        donation = self._make_donation()
        event = self._event_for(donation)

        fake_stripe = type(
            'FakeStripe',
            (),
            {
                'Webhook': type('FakeWebhook', (), {'construct_event': staticmethod(lambda payload, sig, secret: event)}),
                'error': type('FakeError', (), {'SignatureVerificationError': Exception}),
            },
        )
        mock_client.return_value = (fake_stripe, None)

        response_one = self.client.post(
            '/donate/stripe/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )
        response_two = self.client.post(
            '/donate/stripe/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )

        donation.refresh_from_db()
        self.assertEqual(response_one.status_code, 200)
        self.assertEqual(response_two.status_code, 200)
        self.assertEqual(donation.status, 'completed')
        self.assertEqual(StripeWebhookEvent.objects.filter(event_id='evt_001').count(), 1)
        self.assertEqual(mock_send_email.call_count, 1)

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('donations.views.PaymentSuccessView.send_confirmation_email')
    @patch('donations.views._extract_card_last4', return_value='4242')
    @patch('donations.views._get_stripe_client')
    def test_metadata_mismatch_does_not_complete_donation(self, mock_client, _mock_last4, mock_send_email):
        donation = self._make_donation()
        event = self._event_for(donation, event_id='evt_002', metadata_ref='wrong-ref')

        fake_stripe = type(
            'FakeStripe',
            (),
            {
                'Webhook': type('FakeWebhook', (), {'construct_event': staticmethod(lambda payload, sig, secret: event)}),
                'error': type('FakeError', (), {'SignatureVerificationError': Exception}),
            },
        )
        mock_client.return_value = (fake_stripe, None)

        response = self.client.post(
            '/donate/stripe/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )

        donation.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(donation.status, 'pending')
        self.assertEqual(mock_send_email.call_count, 0)


class StripeWebhookFailurePathTest(TestCase):

    def _make_donation(self):
        return Donation.objects.create(
            amount=Decimal('31.00'),
            status='pending',
            donor_email='failed@example.com',
            transaction_ref='txn-failed-001',
            stripe_session_id='cs_test_failed',
            payment_method='card',
        )

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('donations.views._get_stripe_client')
    def test_signature_verification_error_returns_400(self, mock_client):
        class FakeSignatureError(Exception):
            pass

        class FakeWebhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                raise FakeSignatureError('bad signature')

        fake_stripe = type(
            'FakeStripe',
            (),
            {
                'Webhook': FakeWebhook,
                'error': type('FakeError', (), {'SignatureVerificationError': FakeSignatureError}),
            },
        )
        mock_client.return_value = (fake_stripe, None)

        response = self.client.post(
            '/donate/stripe/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='bad_sig',
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('donations.views._get_stripe_client')
    def test_payment_intent_failed_by_intent_id_marks_failed(self, mock_client):
        donation = self._make_donation()
        donation.stripe_payment_intent_id = 'pi_fail_1'
        donation.save(update_fields=['stripe_payment_intent_id'])

        event = {
            'id': 'evt_fail_1',
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_fail_1',
                    'metadata': {
                        'donation_id': str(donation.pk),
                        'transaction_ref': donation.transaction_ref,
                    },
                }
            },
        }
        fake_stripe = type(
            'FakeStripe',
            (),
            {
                'Webhook': type('FakeWebhook', (), {'construct_event': staticmethod(lambda payload, sig, secret: event)}),
                'error': type('FakeError', (), {'SignatureVerificationError': Exception}),
            },
        )
        mock_client.return_value = (fake_stripe, None)

        response = self.client.post(
            '/donate/stripe/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )
        donation.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(donation.status, 'failed')

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('donations.views._get_stripe_client')
    def test_payment_intent_failed_falls_back_to_metadata_donation_id(self, mock_client):
        donation = self._make_donation()

        event = {
            'id': 'evt_fail_2',
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_fail_2',
                    'metadata': {
                        'donation_id': str(donation.pk),
                        'transaction_ref': donation.transaction_ref,
                    },
                }
            },
        }
        fake_stripe = type(
            'FakeStripe',
            (),
            {
                'Webhook': type('FakeWebhook', (), {'construct_event': staticmethod(lambda payload, sig, secret: event)}),
                'error': type('FakeError', (), {'SignatureVerificationError': Exception}),
            },
        )
        mock_client.return_value = (fake_stripe, None)

        response = self.client.post(
            '/donate/stripe/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )
        donation.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(donation.status, 'failed')
        self.assertEqual(donation.stripe_payment_intent_id, 'pi_fail_2')

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('donations.views._get_stripe_client')
    def test_payment_intent_failed_mismatch_ref_does_not_update(self, mock_client):
        donation = self._make_donation()

        event = {
            'id': 'evt_fail_3',
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_fail_3',
                    'metadata': {
                        'donation_id': str(donation.pk),
                        'transaction_ref': 'wrong-ref',
                    },
                }
            },
        }
        fake_stripe = type(
            'FakeStripe',
            (),
            {
                'Webhook': type('FakeWebhook', (), {'construct_event': staticmethod(lambda payload, sig, secret: event)}),
                'error': type('FakeError', (), {'SignatureVerificationError': Exception}),
            },
        )
        mock_client.return_value = (fake_stripe, None)

        response = self.client.post(
            '/donate/stripe/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )
        donation.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(donation.status, 'pending')
        self.assertFalse(donation.stripe_payment_intent_id)
