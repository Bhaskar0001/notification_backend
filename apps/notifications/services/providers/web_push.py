import logging
import requests
from django.conf import settings
from apps.notifications.models import PushSubscription
from .base import NotificationProvider

logger = logging.getLogger(__name__)


class WebPushProvider(NotificationProvider):
    """
    Delivers Web Push notifications using OneSignal REST API.
    """

    API_URL = "https://api.onesignal.com/notifications"

    def send(self, notification):
        app_id = getattr(settings, 'ONESIGNAL_APP_ID', '')
        rest_api_key = getattr(settings, 'ONESIGNAL_REST_API_KEY', '')

        if not app_id or not rest_api_key:
            return False, None, "OneSignal credentials not configured (ONESIGNAL_APP_ID or ONESIGNAL_REST_API_KEY missing)."

        # Fetch active push subscriptions for user
        active_subs = PushSubscription.objects.filter(
            user=notification.user,
            is_active=True
        ).values_list('onesignal_subscription_id', flat=True)

        subscription_ids = list(active_subs)
        if not subscription_ids:
            return False, None, f"User {notification.user.email} has no active browser push subscriptions."

        title = notification.rendered_payload.get('title') or notification.trigger.name or "Notification"
        body_text = notification.rendered_payload.get('body', '')

        headers = {
            'Authorization': f'Key {rest_api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'app_id': app_id,
            'include_subscription_ids': subscription_ids,
            'headings': {'en': title},
            'contents': {'en': body_text},
        }

        try:
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=20)
            status_code = response.status_code

            try:
                response_data = response.json()
            except Exception:
                response_data = {'raw_text': response.text}

            if 200 <= status_code < 300:
                # OneSignal can return 200 with errors if player IDs were invalid
                errors = response_data.get('errors')
                recipients = response_data.get('recipients', 0)
                msg_id = response_data.get('id', '')

                if errors and recipients == 0:
                    return False, {
                        'status_code': status_code,
                        'data': response_data,
                    }, f"OneSignal warning: {errors}"

                return True, {
                    'status_code': status_code,
                    'message_id': msg_id,
                    'recipients': recipients,
                    'data': response_data,
                }, None
            else:
                errors = response_data.get('errors')
                error_msg = str(errors) if errors else (response.text or f"HTTP {status_code}")
                return False, {
                    'status_code': status_code,
                    'data': response_data,
                }, f"OneSignal API error ({status_code}): {error_msg}"

        except requests.Timeout as te:
            logger.error(f"OneSignal API timeout: {te}")
            return False, {'status_code': 504}, f"Network timeout contacting OneSignal API: {str(te)}"
        except requests.RequestException as re:
            logger.error(f"OneSignal API request error: {re}")
            return False, {'status_code': 502}, f"Network error contacting OneSignal API: {str(re)}"
        except Exception as e:
            logger.error(f"Unexpected OneSignal error: {e}")
            return False, None, f"Unexpected error in OneSignal provider: {str(e)}"
