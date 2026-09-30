from rest_framework import serializers
from .models import (
    Trigger,
    NotificationTemplate,
    NotificationEvent,
    Notification,
    DeliveryAttempt,
    PushSubscription,
)
from apps.accounts.serializers import UserSerializer


class ChannelStatusSerializer(serializers.Serializer):
    configured = serializers.BooleanField()
    enabled = serializers.BooleanField()
    template_id = serializers.UUIDField(allow_null=True)
    template_name = serializers.CharField(allow_null=True)


class TriggerListSerializer(serializers.ModelSerializer):
    whatsapp = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    web_push = serializers.SerializerMethodField()

    class Meta:
        model = Trigger
        fields = [
            'id',
            'name',
            'event_key',
            'description',
            'is_active',
            'whatsapp',
            'email',
            'web_push',
            'created_at',
            'updated_at',
        ]

    def _get_channel_info(self, obj, channel_code):
        template = obj.templates.filter(channel=channel_code).first()
        if template:
            return {
                'configured': True,
                'enabled': template.is_enabled,
                'template_id': template.id,
                'template_name': template.name,
            }
        return {
            'configured': False,
            'enabled': False,
            'template_id': None,
            'template_name': None,
        }

    def get_whatsapp(self, obj):
        return self._get_channel_info(obj, NotificationTemplate.Channel.WHATSAPP)

    def get_email(self, obj):
        return self._get_channel_info(obj, NotificationTemplate.Channel.EMAIL)

    def get_web_push(self, obj):
        return self._get_channel_info(obj, NotificationTemplate.Channel.WEB_PUSH)


class TriggerDetailSerializer(serializers.ModelSerializer):
    templates = serializers.SerializerMethodField()

    class Meta:
        model = Trigger
        fields = [
            'id',
            'name',
            'event_key',
            'description',
            'is_active',
            'templates',
            'created_at',
            'updated_at',
        ]

    def get_templates(self, obj):
        return NotificationTemplateSerializer(obj.templates.all(), many=True).data


class TriggerCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trigger
        fields = ['id', 'name', 'event_key', 'description', 'is_active']

    def validate_event_key(self, value):
        cleaned = value.strip().lower()
        query = Trigger.objects.filter(event_key=cleaned)
        if self.instance:
            query = query.exclude(id=self.instance.id)
        if query.exists():
            raise serializers.ValidationError("A trigger with this event key already exists.")
        return cleaned


class NotificationTemplateSerializer(serializers.ModelSerializer):
    trigger_name = serializers.ReadOnlyField(source='trigger.name')
    trigger_event_key = serializers.ReadOnlyField(source='trigger.event_key')

    class Meta:
        model = NotificationTemplate
        fields = [
            'id',
            'trigger',
            'trigger_name',
            'trigger_event_key',
            'channel',
            'name',
            'subject',
            'title',
            'body',
            'variables',
            'is_enabled',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs):
        trigger = attrs.get('trigger', getattr(self.instance, 'trigger', None))
        channel = attrs.get('channel', getattr(self.instance, 'channel', None))

        if trigger and channel:
            query = NotificationTemplate.objects.filter(trigger=trigger, channel=channel)
            if self.instance:
                query = query.exclude(id=self.instance.id)
            if query.exists():
                raise serializers.ValidationError(
                    {"channel": f"A template for {channel} already exists on this trigger."}
                )

        # Validate channel-specific fields
        if channel == NotificationTemplate.Channel.EMAIL:
            subject = attrs.get('subject', getattr(self.instance, 'subject', ''))
            if not subject:
                raise serializers.ValidationError({"subject": "Email template requires a subject."})

        if channel == NotificationTemplate.Channel.WEB_PUSH:
            title = attrs.get('title', getattr(self.instance, 'title', ''))
            if not title:
                raise serializers.ValidationError({"title": "Web Push template requires a title."})

        return attrs


class DeliveryAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAttempt
        fields = [
            'id',
            'attempt_number',
            'status',
            'provider_response',
            'error_message',
            'created_at',
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')
    user_name = serializers.SerializerMethodField()
    trigger_name = serializers.ReadOnlyField(source='trigger.name')
    event_id = serializers.ReadOnlyField(source='event.event_id')

    class Meta:
        model = Notification
        fields = [
            'id',
            'event_id',
            'user_email',
            'user_name',
            'trigger_name',
            'channel',
            'provider',
            'status',
            'attempt_count',
            'created_at',
            'sent_at',
            'failed_at',
        ]

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class NotificationDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    trigger = TriggerCreateUpdateSerializer(read_only=True)
    template = NotificationTemplateSerializer(read_only=True)
    event_id = serializers.ReadOnlyField(source='event.event_id')
    event_key = serializers.ReadOnlyField(source='event.event_key')
    delivery_attempts = DeliveryAttemptSerializer(many=True, read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'event_id',
            'event_key',
            'user',
            'trigger',
            'template',
            'channel',
            'status',
            'provider',
            'provider_message_id',
            'rendered_payload',
            'attempt_count',
            'error_message',
            'queued_at',
            'sent_at',
            'failed_at',
            'created_at',
            'updated_at',
            'delivery_attempts',
        ]


class PushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ['id', 'onesignal_subscription_id', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_active', 'created_at']

    def validate_onesignal_subscription_id(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Subscription ID cannot be empty.")
        return cleaned
