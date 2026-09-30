import logging
import requests
from django.conf import settings
from .base import NotificationProvider

logger = logging.getLogger(__name__)


class EmailProvider(NotificationProvider):
    """
    Delivers Email notifications using Resend API.
    """

    API_URL = "https://api.resend.com/emails"

    def send(self, notification):
        api_key = getattr(settings, 'RESEND_API_KEY', '')
        from_email = getattr(settings, 'RESEND_FROM_EMAIL', 'onboarding@resend.dev')

        if not api_key:
            return False, None, "Resend API key not configured (RESEND_API_KEY missing)."

        recipient_email = (notification.user.email or '').strip()
        if not recipient_email:
            return False, None, f"User {notification.user.id} has no valid email address."

        subject = notification.rendered_payload.get('subject') or f"Notification from {notification.trigger.name}"
        html_body = notification.rendered_payload.get('body', '')

        headers = {
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'NotificationSystem/1.0',
            'Content-Type': 'application/json',
        }
        payload = {
            'from': from_email,
            'to': [recipient_email],
            'subject': subject,
            'html': html_body,
        }

        try:
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=20)
            status_code = response.status_code

            try:
                response_data = response.json()
            except Exception:
                response_data = {'raw_text': response.text}

            if 200 <= status_code < 300:
                msg_id = response_data.get('id', '')
                return True, {
                    'status_code': status_code,
                    'message_id': msg_id,
                    'data': response_data,
                }, None
            else:
                error_msg = response_data.get('message') or response.text or f"HTTP {status_code}"
                return False, {
                    'status_code': status_code,
                    'data': response_data,
                }, f"Resend API error ({status_code}): {error_msg}"

        except requests.Timeout as te:
            logger.error(f"Resend API timeout: {te}")
            return False, {'status_code': 504}, f"Network timeout contacting Resend API: {str(te)}"
        except requests.RequestException as re:
            logger.error(f"Resend API request error: {re}")
            return False, {'status_code': 502}, f"Network error contacting Resend API: {str(re)}"
        except Exception as e:
            logger.error(f"Unexpected Resend error: {e}")
            return False, None, f"Unexpected error in Resend provider: {str(e)}"
