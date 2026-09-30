from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounts.permissions import IsAdminRole
from .models import (
    Trigger,
    NotificationTemplate,
    Notification,
    PushSubscription,
)
from .serializers import (
    TriggerListSerializer,
    TriggerDetailSerializer,
    TriggerCreateUpdateSerializer,
    NotificationTemplateSerializer,
    NotificationListSerializer,
    NotificationDetailSerializer,
    PushSubscriptionSerializer,
)


class TriggerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Trigger.objects.prefetch_related('templates').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return TriggerListSerializer
        elif self.action in ['retrieve']:
            return TriggerDetailSerializer
        return TriggerCreateUpdateSerializer


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = NotificationTemplate.objects.select_related('trigger').all()
    serializer_class = NotificationTemplateSerializer
    filterset_fields = ['trigger', 'channel', 'is_enabled']


class TemplateToggleView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        template = get_object_or_404(NotificationTemplate, pk=pk)
        template.is_enabled = not template.is_enabled
        template.save(update_fields=['is_enabled', 'updated_at'])
        return Response(
            NotificationTemplateSerializer(template).data,
            status=status.HTTP_200_OK,
        )


class TemplateTestSendView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        template = get_object_or_404(NotificationTemplate, pk=pk)
        target_user = request.user

        # Render template for test
        from apps.notifications.services.renderer import TemplateRenderer
        from apps.notifications.services.notification_service import NotificationService
        from apps.notifications.models import NotificationEvent, Notification

        rendered = {
            'body': TemplateRenderer.render(template.body, target_user),
        }
        if template.subject:
            rendered['subject'] = TemplateRenderer.render(template.subject, target_user)
        if template.title:
            rendered['title'] = TemplateRenderer.render(template.title, target_user)

        event = NotificationEvent.objects.create(
            event_id=timezone.now().timestamp(),
            event_key=f"test.{template.channel.lower()}",
            user=target_user,
            payload={'is_test': True},
            processed_at=timezone.now(),
        )

        notification = Notification.objects.create(
            event=event,
            user=target_user,
            trigger=template.trigger,
            template=template,
            channel=template.channel,
            status=Notification.Status.PROCESSING,
            provider={
                'WHATSAPP': 'meta_whatsapp',
                'EMAIL': 'resend',
                'WEB_PUSH': 'onesignal',
            }.get(template.channel, 'test_provider'),
            rendered_payload=rendered,
            queued_at=timezone.now(),
        )

        service = NotificationService()
        success, provider_response, error = service.send(notification)

        from apps.notifications.models import DeliveryAttempt
        notification.attempt_count = 1
        DeliveryAttempt.objects.create(
            notification=notification,
            attempt_number=1,
            status='SENT' if success else 'FAILED',
            provider_response=provider_response or {},
            error_message=error or '',
        )

        if success:
            notification.status = Notification.Status.SENT
            notification.sent_at = timezone.now()
            if provider_response and 'message_id' in provider_response:
                notification.provider_message_id = provider_response['message_id']
            notification.save()
            return Response(
                {
                    'status': 'sent',
                    'notification_id': str(notification.id),
                    'provider_response': provider_response,
                },
                status=status.HTTP_200_OK,
            )
        else:
            notification.status = Notification.Status.FAILED
            notification.failed_at = timezone.now()
            notification.error_message = error or ''
            notification.save()
            return Response(
                {
                    'status': 'failed',
                    'notification_id': str(notification.id),
                    'error': error,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Notification.objects.select_related('user', 'trigger', 'template', 'event').prefetch_related('delivery_attempts').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        channel_param = self.request.query_params.get('channel')
        if channel_param:
            qs = qs.filter(channel=channel_param.upper())
        return qs


class AdminStatsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        total_triggers = Trigger.objects.count()
        configured_templates = NotificationTemplate.objects.count()
        failed_notifications = Notification.objects.filter(status=Notification.Status.FAILED).count()
        recent_notifications = Notification.objects.select_related('user', 'trigger', 'event').order_by('-created_at')[:5]

        return Response(
            {
                'total_triggers': total_triggers,
                'configured_templates': configured_templates,
                'failed_notifications': failed_notifications,
                'recent_notifications': NotificationListSerializer(recent_notifications, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class PushSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_sub = PushSubscription.objects.filter(user=request.user, is_active=True).first()
        return Response(
            {
                'is_subscribed': active_sub is not None,
                'subscription_id': active_sub.onesignal_subscription_id if active_sub else None,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        sub_id = request.data.get('onesignal_subscription_id')
        if not sub_id:
            return Response(
                {"onesignal_subscription_id": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription, created = PushSubscription.objects.update_or_create(
            user=request.user,
            onesignal_subscription_id=sub_id,
            defaults={'is_active': True},
        )

        return Response(
            PushSubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        PushSubscription.objects.filter(user=request.user).update(is_active=False)
        return Response({"detail": "Push subscription removed."}, status=status.HTTP_200_OK)
