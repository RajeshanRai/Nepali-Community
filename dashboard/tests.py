from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse

from dashboard.decorators import staff_required, superuser_required

User = get_user_model()


class StaffRequiredDecoratorTest(TestCase):

    def test_active_staff_passes(self):
        user = User(is_active=True, is_staff=True)
        self.assertTrue(staff_required(user))

    def test_inactive_staff_fails(self):
        user = User(is_active=False, is_staff=True)
        self.assertFalse(staff_required(user))

    def test_active_non_staff_fails(self):
        user = User(is_active=True, is_staff=False)
        self.assertFalse(staff_required(user))

    def test_anonymous_user_fails(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(staff_required(AnonymousUser()))


class SuperuserRequiredDecoratorTest(TestCase):

    def test_superuser_passes(self):
        user = User(is_active=True, is_superuser=True)
        self.assertTrue(superuser_required(user))

    def test_non_superuser_fails(self):
        user = User(is_active=True, is_superuser=False)
        self.assertFalse(superuser_required(user))


class DashboardAccessTest(TestCase):
    """Dashboard pages must redirect non-staff to login."""

    def test_anonymous_redirected_from_dashboard(self):
        response = self.client.get('/dashboard/', follow=False)
        self.assertIn(response.status_code, [302, 301])

    def test_non_staff_redirected_from_dashboard(self):
        User.objects.create_user(username='regular', password='pass', email='r@e.com')
        self.client.login(username='regular', password='pass')
        response = self.client.get('/dashboard/', follow=False)
        self.assertIn(response.status_code, [302, 301])

    def test_staff_can_access_dashboard(self):
        staff = User.objects.create_user(
            username='staffuser', password='pass', email='s@e.com',
            is_staff=True,
        )
        self.client.login(username='staffuser', password='pass')
        response = self.client.get('/dashboard/admin/users/profiles/')
        self.assertEqual(response.status_code, 200)
