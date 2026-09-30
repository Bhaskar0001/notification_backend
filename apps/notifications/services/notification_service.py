from apps.notifications.models import NotificationTemplate
from .providers.whatsapp import WhatsAppProvider
from .providers.email import EmailProvider
from .providers.web_push import WebPushProvider


class NotificationService:
    """
    Central notification delivery service.
    Instantiates and invokes the appropriate provider based on the notification's channel.
    """

    PROVIDERS = {
        NotificationTemplate.Channel.WHATSAPP: WhatsAppProvider,
        NotificationTemplate.Channel.EMAIL: EmailProvider,
        NotificationTemplate.Channel.WEB_PUSH: WebPushProvider,
    }

    def send(self, notification):
        channel = notification.channel
        provider_class = self.PROVIDERS.get(channel)
        if not provider_class:
            return False, None, f"Unsupported notification channel: {channel}"

        provider = provider_class()
        return provider.send(notification)
