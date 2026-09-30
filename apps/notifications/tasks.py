import logging
from celery import shared_task
from django.utils import timezone
from apps.notifications.models import Notification, DeliveryAttempt
from apps.notifications.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_DELAYS = [60, 300, 900]  # 1 min, 5 min, 15 min


def is_retryable_error(status_code: int = None, error_message: str = '') -> bool:
    """Determine if a provider error is temporary and eligible for retry."""
    if status_code in (429, 500, 502, 503, 504):
        return True
    lower_err = (error_message or '').lower()
    if 'timeout' in lower_err or 'connection' in lower_err or 'network' in lower_err:
        return True
    return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_task(self, notification_id: str):
    """
    Asynchronous task to process and deliver a single notification.
    Enforces idempotency, records every delivery attempt, and handles retries.
    """
    try:
        notification = Notification.objects.select_related('user', 'trigger', 'template').get(id=notification_id)
    except Notification.DoesNotExist:
        logger.warning(f"Notification with id {notification_id} not found.")
        return

    # Idempotency guard: do not re-send already delivered notifications
    if notification.status == Notification.Status.SENT:
        logger.info(f"Notification {notification_id} is already SENT. Skipping.")
        return

    notification.status = Notification.Status.PROCESSING
    notification.save(update_fields=['status', 'updated_at'])

    service = NotificationService()
    success, provider_response, error = service.send(notification)

    attempt_number = notification.attempt_count + 1
    notification.attempt_count = attempt_number

    # Record delivery attempt
    DeliveryAttempt.objects.create(
        notification=notification,
        attempt_number=attempt_number,
        status='SENT' if success else 'FAILED',
        provider_response=provider_response or {},
        error_message=error or '',
    )

    if success:
        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.error_message = ''
        if provider_response and 'message_id' in provider_response:
            notification.provider_message_id = provider_response['message_id']
        notification.save(update_fields=['status', 'sent_at', 'provider_message_id', 'error_message', 'attempt_count', 'updated_at'])
        logger.info(f"Notification {notification_id} sent successfully via {notification.channel}.")
    else:
        status_code = None
        if provider_response and isinstance(provider_response, dict):
            status_code = provider_response.get('status_code')

        can_retry = (attempt_number < MAX_ATTEMPTS) and is_retryable_error(status_code, error)

        if can_retry:
            delay = RETRY_DELAYS[min(attempt_number - 1, len(RETRY_DELAYS) - 1)]
            notification.status = Notification.Status.PENDING
            notification.error_message = error or ''
            notification.save(update_fields=['status', 'error_message', 'attempt_count', 'updated_at'])
            logger.warning(f"Notification {notification_id} failed (attempt {attempt_number}). Retrying in {delay}s. Error: {error}")
            raise self.retry(countdown=delay, exc=Exception(error))
        else:
            notification.status = Notification.Status.FAILED
            notification.failed_at = timezone.now()
            notification.error_message = error or ''
            notification.save(update_fields=['status', 'failed_at', 'error_message', 'attempt_count', 'updated_at'])
            logger.error(f"Notification {notification_id} permanently failed after attempt {attempt_number}. Error: {error}")
