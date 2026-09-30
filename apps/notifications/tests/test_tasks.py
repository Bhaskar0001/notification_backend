import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase
from apps.accounts.models import User
from apps.notifications.models import (
    Trigger,
    NotificationTemplate,
    NotificationEvent,
    Notification,
    DeliveryAttempt,
)
from apps.notifications.tasks import send_notification_task


class NotificationTaskDeliveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='delivery@example.com',
            first_name='Delivery',
            last_name='Tester',
            phone='+18887776666',
            password='Password123!',
        )
        self.trigger = Trigger.objects.create(
            name='Login',
            event_key='user.login',
        )
        self.template = NotificationTemplate.objects.create(
            trigger=self.trigger,
            channel='EMAIL',
            name='Email Notification',
            subject='Subject',
            body='Hello {{user.first_name}}',
        )
        self.event = NotificationEvent.objects.create(
            event_id=uuid.uuid4(),
            event_key='user.login',
            user=self.user,
        )
        self.notification = Notification.objects.create(
            event=self.event,
            user=self.user,
            trigger=self.trigger,
            template=self.template,
            channel='EMAIL',
            status=Notification.Status.PENDING,
            provider='resend',
            rendered_payload={'subject': 'Subject', 'body': 'Hello Delivery'},
        )

    @patch('apps.notifications.services.notification_service.NotificationService.send')
    def test_successful_task_delivery(self, mock_send):
        mock_send.return_value = (True, {'status_code': 200, 'message_id': 're_msg_12345'}, None)

        send_notification_task(str(self.notification.id))

        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, Notification.Status.SENT)
        self.assertEqual(self.notification.provider_message_id, 're_msg_12345')
        self.assertEqual(self.notification.attempt_count, 1)

        # Check delivery attempt recorded
        attempt = DeliveryAttempt.objects.get(notification=self.notification)
        self.assertEqual(attempt.status, 'SENT')
        self.assertEqual(attempt.attempt_number, 1)

    @patch('apps.notifications.services.notification_service.NotificationService.send')
    def test_non_retryable_error_marks_failed(self, mock_send):
        # 401 Unauthorized is non-retryable
        mock_send.return_value = (False, {'status_code': 401}, 'Invalid API Key')

        send_notification_task(str(self.notification.id))

        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, Notification.Status.FAILED)
        self.assertEqual(self.notification.attempt_count, 1)
        self.assertIn('Invalid API Key', self.notification.error_message)

        attempt = DeliveryAttempt.objects.get(notification=self.notification)
        self.assertEqual(attempt.status, 'FAILED')

    @patch('apps.notifications.services.notification_service.NotificationService.send')
    def test_already_sent_notification_skipped(self, mock_send):
        self.notification.status = Notification.Status.SENT
        self.notification.save()

        send_notification_task(str(self.notification.id))

        mock_send.assert_not_called()
