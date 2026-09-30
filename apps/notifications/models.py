import uuid
from django.db import models
from django.conf import settings


class Trigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    event_key = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.event_key})"


class NotificationTemplate(models.Model):
    class Channel(models.TextChoices):
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        EMAIL = 'EMAIL', 'Email'
        WEB_PUSH = 'WEB_PUSH', 'Web Push'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trigger = models.ForeignKey(Trigger, on_delete=models.CASCADE, related_name='templates')
    channel = models.CharField(max_length=20, choices=Channel.choices)
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    variables = models.JSONField(default=list, blank=True)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['trigger', 'channel'],
                name='unique_trigger_channel'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.trigger.name} - {self.channel} ({'Enabled' if self.is_enabled else 'Disabled'})"


class NotificationEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, db_index=True)
    event_key = models.CharField(max_length=255, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_events'
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Event {self.event_key} - {self.event_id} ({self.user.email})"


class Notification(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        NotificationEvent,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    trigger = models.ForeignKey(
        Trigger,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    channel = models.CharField(max_length=20, choices=NotificationTemplate.Channel.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=50, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    rendered_payload = models.JSONField(default=dict, blank=True)
    attempt_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    queued_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'channel'],
                name='unique_event_channel'
            )
        ]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['channel']),
            models.Index(fields=['user', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification {self.channel} to {self.user.email} [{self.status}]"


class DeliveryAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='delivery_attempts'
    )
    attempt_number = models.IntegerField()
    status = models.CharField(max_length=20)
    provider_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['notification', 'attempt_number'],
                name='unique_notification_attempt'
            )
        ]
        ordering = ['attempt_number']

    def __str__(self):
        return f"Attempt {self.attempt_number} for {self.notification.id} [{self.status}]"


class PushSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_subscriptions'
    )
    onesignal_subscription_id = models.CharField(max_length=255, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Subscription {self.onesignal_subscription_id[:10]}... ({self.user.email})"
