from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------------------------
# Authentication views
# ---------------------------------------------------------------------------

class LoginViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='loginuser',
            password='TestPass123!',
            email='login@example.com',
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_valid_credentials_redirect(self):
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'TestPass123!',
        }, follow=True)
        self.assertTrue(response.context['user'].is_authenticated)

    def test_invalid_credentials_stay_on_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'wrongpassword',
        })
        self.assertFalse(response.context['user'].is_authenticated)


class RegisterViewTest(TestCase):

    def test_register_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_registration_creates_user(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass99!',
            'password_confirm': 'StrongPass99!',
            'first_name': 'New',
            'last_name': 'User',
        }, follow=True)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_duplicate_username_fails(self):
        User.objects.create_user(username='taken', password='pass', email='t@example.com')
        response = self.client.post(reverse('register'), {
            'username': 'taken',
            'email': 'other@example.com',
            'password': 'StrongPass99!',
            'password_confirm': 'StrongPass99!',
        })
        self.assertEqual(User.objects.filter(username='taken').count(), 1)


# ---------------------------------------------------------------------------
# CustomUser model
# ---------------------------------------------------------------------------

class CustomUserModelTest(TestCase):

    def test_display_name_full_name(self):
        user = User(first_name='Jane', last_name='Doe', username='janedoe')
        self.assertEqual(user.display_name, 'Jane Doe')

    def test_display_name_falls_back_to_username(self):
        user = User(username='janedoe')
        self.assertEqual(user.display_name, 'janedoe')

    def test_initials_from_full_name(self):
        user = User(first_name='Jane', last_name='Doe', username='janedoe')
        self.assertEqual(user.initials, 'JD')

    def test_initials_single_name(self):
        user = User(username='ab')
        self.assertEqual(len(user.initials), 2)

    def test_str(self):
        user = User(username='alice')
        self.assertEqual(str(user), 'alice')
