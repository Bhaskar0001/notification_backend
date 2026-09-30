from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.notifications.models import Trigger, NotificationTemplate


class AdminTriggerAndTemplateTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@test.com',
            first_name='Admin',
            last_name='User',
            phone='+1111111111',
            password='AdminPassword123!',
        )
        self.normal_user = User.objects.create_user(
            email='user@test.com',
            first_name='Regular',
            last_name='User',
            phone='+2222222222',
            password='UserPassword123!',
        )
        self.trigger = Trigger.objects.create(
            name='Test Trigger',
            event_key='test.event',
            description='A test trigger',
            is_active=True,
        )
        self.trigger_list_url = reverse('admin-triggers-list')
        self.trigger_detail_url = reverse('admin-triggers-detail', kwargs={'pk': self.trigger.id})
        self.template_list_url = reverse('admin-templates-list')

    def test_normal_user_denied_access_to_triggers(self):
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(self.trigger_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_triggers(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.trigger_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include channel statuses in trigger list
        self.assertIn('whatsapp', response.data['results'][0])
        self.assertIn('email', response.data['results'][0])
        self.assertIn('web_push', response.data['results'][0])

    def test_admin_create_trigger(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'name': 'New Order',
            'event_key': 'order.created',
            'description': 'When order is created',
            'is_active': True,
        }
        response = self.client.post(self.trigger_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Trigger.objects.filter(event_key='order.created').exists())

    def test_admin_create_template(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'trigger': str(self.trigger.id),
            'channel': 'EMAIL',
            'name': 'Welcome Email',
            'subject': 'Welcome to our platform',
            'body': '<p>Hello {{user.first_name}}</p>',
            'is_enabled': True,
        }
        response = self.client.post(self.template_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(NotificationTemplate.objects.filter(trigger=self.trigger, channel='EMAIL').exists())

    def test_duplicate_channel_template_rejected(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'trigger': str(self.trigger.id),
            'channel': 'EMAIL',
            'name': 'First Email',
            'subject': 'First',
            'body': 'Body 1',
        }
        self.client.post(self.template_list_url, data, format='json')
        # Second template for same trigger and channel must fail
        data2 = {
            'trigger': str(self.trigger.id),
            'channel': 'EMAIL',
            'name': 'Second Email',
            'subject': 'Second',
            'body': 'Body 2',
        }
        response = self.client.post(self.template_list_url, data2, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_template_toggle(self):
        self.client.force_authenticate(user=self.admin)
        template = NotificationTemplate.objects.create(
            trigger=self.trigger,
            channel='WHATSAPP',
            name='WhatsApp Alert',
            body='Hello {{user.first_name}}',
            is_enabled=True,
        )
        toggle_url = reverse('admin-template-toggle', kwargs={'pk': template.id})
        response = self.client.patch(toggle_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        template.refresh_from_db()
        self.assertFalse(template.is_enabled)
