import uuid
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User


class AccountsAuthTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('auth-register')
        self.login_url = reverse('auth-login')
        self.logout_url = reverse('auth-logout')
        self.me_url = reverse('auth-me')
        self.user_profile_url = reverse('user-profile-me')

        self.user_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone': '+1234567890',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        }

    def test_registration_success(self):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertEqual(response.data['user']['email'], 'john.doe@example.com')
        self.assertEqual(response.data['user']['role'], 'USER')
        self.assertTrue(User.objects.filter(email='john.doe@example.com').exists())

    def test_registration_password_mismatch(self):
        data = self.user_data.copy()
        data['confirm_password'] = 'DifferentPassword123!'
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirm_password', response.data)

    def test_registration_duplicate_email(self):
        self.client.post(self.register_url, self.user_data, format='json')
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_login_success(self):
        self.client.post(self.register_url, self.user_data, format='json')
        login_data = {
            'email': 'john.doe@example.com',
            'password': 'StrongPassword123!',
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertIn('user', response.data)

        # Check last_login_at is updated
        user = User.objects.get(email='john.doe@example.com')
        self.assertIsNotNone(user.last_login_at)

    def test_login_invalid_credentials(self):
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'WrongPassword123!',
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_endpoint_authenticated(self):
        reg_response = self.client.post(self.register_url, self.user_data, format='json')
        access_token = reg_response.data['tokens']['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'john.doe@example.com')

    def test_me_endpoint_unauthenticated(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_update(self):
        reg_response = self.client.post(self.register_url, self.user_data, format='json')
        access_token = reg_response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        update_data = {
            'first_name': 'Johnny',
            'last_name': 'Smith',
            'phone': '+9999999999',
        }
        response = self.client.patch(self.user_profile_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Johnny')
        self.assertEqual(response.data['last_name'], 'Smith')
        self.assertEqual(response.data['phone'], '+9999999999')
        # Email cannot be changed
        self.assertEqual(response.data['email'], 'john.doe@example.com')
