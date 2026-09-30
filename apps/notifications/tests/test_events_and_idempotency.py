import uuid
from unittest.mock import patch
from django.test import TestCase
from apps.accounts.models import User
from apps.notifications.models import (
    Trigger,
    NotificationTemplate,
    NotificationEvent,
    Notification,
    PushSubscription,
)
from apps.notifications.services.event_service import NotificationEventService


class EventAndIdempotencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='bob@example.com',
            first_name='Bob',
            last_name='Builder',
            phone='+19998887777',
            password='Password123!',
        )
        self.login_trigger = Trigger.objects.create(
            name='Login',
            event_key='user.login',
            description='Login trigger',
            is_active=True,
        )
        # Email template (Enabled)
        self.email_template = NotificationTemplate.objects.create(
            trigger=self.login_trigger,
            channel='EMAIL',
            name='Login Email',
            subject='Login from {{user.email}}',
            body='Hello {{user.first_name}}, you logged in.',
            is_enabled=True,
        )
        # WhatsApp template (Disabled)
        self.whatsapp_template = NotificationTemplate.objects.create(
            trigger=self.login_trigger,
            channel='WHATSAPP',
            name='Login WhatsApp',
            body='WhatsApp: {{user.first_name}} logged in.',
            is_enabled=False,
        )
        # Web Push template (Enabled)
        self.push_template = NotificationTemplate.objects.create(
            trigger=self.login_trigger,
            channel='WEB_PUSH',
            name='Login Push',
            title='Login alert',
            body='Push: {{user.first_name}} logged in.',
            is_enabled=True,
        )

    @patch('apps.notifications.tasks.send_notification_task.delay')
    def test_emit_event_creates_notifications_for_enabled_channels_only(self, mock_delay):
        event = NotificationEventService.emit('user.login', self.user)
        self.assertIsNotNone(event)
        self.assertEqual(event.event_key, 'user.login')
        self.assertEqual(event.user, self.user)

        # Check notifications generated
        notifications = Notification.objects.filter(event=event)
        # Email and Web Push are enabled, WhatsApp is disabled -> exactly 2 notifications
        self.assertEqual(notifications.count(), 2)

        channels = list(notifications.values_list('channel', flat=True))
        self.assertIn('EMAIL', channels)
        self.assertIn('WEB_PUSH', channels)
        self.assertNotIn('WHATSAPP', channels)

        # Check rendered payloads
        email_notif = notifications.get(channel='EMAIL')
        self.assertEqual(email_notif.rendered_payload['subject'], 'Login from bob@example.com')
        self.assertEqual(email_notif.rendered_payload['body'], 'Hello Bob, you logged in.')

        # Check tasks queued
        self.assertEqual(mock_delay.call_count, 2)

    @patch('apps.notifications.tasks.send_notification_task.delay')
    def test_idempotency_prevents_duplicate_notifications(self, mock_delay):
        custom_id = uuid.uuid4()
        # First emission
        event1 = NotificationEventService.emit('user.login', self.user, custom_event_id=custom_id)
        count_first = Notification.objects.filter(event=event1).count()
        self.assertEqual(count_first, 2)

        # Second emission with same event_id
        event2 = NotificationEventService.emit('user.login', self.user, custom_event_id=custom_id)
        count_second = Notification.objects.filter(event=event2).count()

        # Must not duplicate
        self.assertEqual(count_second, 2)
        self.assertEqual(Notification.objects.filter(event__event_id=custom_id).count(), 2)
