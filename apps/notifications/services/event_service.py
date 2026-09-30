import uuid
import logging
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.notifications.models import (
    Trigger,
    NotificationTemplate,
    NotificationEvent,
    Notification,
)
from apps.notifications.services.renderer import TemplateRenderer

logger = logging.getLogger(__name__)


class NotificationEventService:
    """
    Core event emission service.
    Receives events, finds matching triggers and enabled templates,
    creates notification records, and queues Celery delivery tasks.
    """

    @classmethod
    def emit(cls, event_key: str, user, payload: dict = None, custom_event_id: uuid.UUID = None):
        """
        Emits an event into the notification pipeline.
        
        Args:
            event_key: Unique identifier of the event (e.g. 'user.login', 'user.logout')
            user: The User instance triggering or associated with the event
            payload: Optional JSON dictionary containing event context
            custom_event_id: Optional UUID to force specific event ID for idempotency testing
        
        Returns:
            NotificationEvent instance or None
        """
        if not user or not user.is_authenticated:
            logger.warning(f"NotificationEventService: user must be authenticated. Event {event_key} skipped.")
            return None

        event_id = custom_event_id or uuid.uuid4()
        payload = payload or {}

        # 1. Find trigger and ensure active
        try:
            trigger = Trigger.objects.get(event_key=event_key, is_active=True)
        except Trigger.DoesNotExist:
            logger.info(f"NotificationEventService: No active trigger for event_key='{event_key}'. Skipped.")
            return None

        # 2. Check and Create Event Record (with idempotency guard)
        existing_event = NotificationEvent.objects.filter(event_id=event_id).first()
        if existing_event:
            logger.warning(f"NotificationEventService: Event with ID {event_id} already exists (idempotency guard).")
            return existing_event

        try:
            with transaction.atomic():
                event = NotificationEvent.objects.create(
                    event_id=event_id,
                    event_key=event_key,
                    user=user,
                    payload=payload,
                )
        except IntegrityError:
            logger.warning(f"NotificationEventService: Event with ID {event_id} already exists (concurrent guard).")
            return NotificationEvent.objects.filter(event_id=event_id).first()

        # 3. Find all enabled templates for this trigger
        templates = NotificationTemplate.objects.filter(
            trigger=trigger,
            is_enabled=True,
        )

        if not templates.exists():
            logger.info(f"NotificationEventService: Trigger '{trigger.name}' has no enabled templates.")
            event.processed_at = timezone.now()
            event.save(update_fields=['processed_at'])
            return event

        # 4. Generate notification records & queue tasks
        from apps.notifications.tasks import send_notification_task

        now = timezone.now()
        created_notifications = []

        for template in templates:
            rendered_payload = {
                'body': TemplateRenderer.render(template.body, user, now),
            }
            if template.subject:
                rendered_payload['subject'] = TemplateRenderer.render(template.subject, user, now)
            if template.title:
                rendered_payload['title'] = TemplateRenderer.render(template.title, user, now)

            provider_name = {
                NotificationTemplate.Channel.WHATSAPP: 'meta_whatsapp',
                NotificationTemplate.Channel.EMAIL: 'resend',
                NotificationTemplate.Channel.WEB_PUSH: 'onesignal',
            }.get(template.channel, 'default_provider')

            try:
                with transaction.atomic():
                    notification = Notification.objects.create(
                        event=event,
                        user=user,
                        trigger=trigger,
                        template=template,
                        channel=template.channel,
                        status=Notification.Status.PENDING,
                        provider=provider_name,
                        rendered_payload=rendered_payload,
                        queued_at=now,
                    )
                    created_notifications.append(notification)
            except IntegrityError:
                # Idempotency guard: duplicate (event, channel) prevented by UniqueConstraint
                logger.warning(f"Notification for event {event.id} and channel {template.channel} already created.")
                continue

            # Queue Celery task
            try:
                send_notification_task.delay(str(notification.id))
            except Exception as task_exc:
                logger.error(f"Failed to enqueue Celery task for notification {notification.id}: {task_exc}")

        event.processed_at = timezone.now()
        event.save(update_fields=['processed_at'])
        return event
