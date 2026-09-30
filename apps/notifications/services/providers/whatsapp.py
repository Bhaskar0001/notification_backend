import logging
import requests
from django.conf import settings
from .base import NotificationProvider

logger = logging.getLogger(__name__)


class WhatsAppProvider(NotificationProvider):
    """
    Delivers WhatsApp notifications using Twilio WhatsApp Sandbox or Meta WhatsApp Cloud API.
    """

    def send(self, notification):
        # 1. Check Twilio WhatsApp credentials first
        twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        twilio_from = getattr(settings, 'TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

        recipient_phone = (notification.user.phone or '').strip()
        body_text = notification.rendered_payload.get('body', '')

        if not recipient_phone:
            return False, None, f"User {notification.user.email} has no phone number configured."

        if not body_text:
            return False, None, "Message body cannot be empty."

        # If Twilio credentials are configured, deliver via Twilio WhatsApp Sandbox
        if twilio_sid and twilio_token:
            clean_phone = recipient_phone if recipient_phone.startswith('+') else f"+{recipient_phone}"
            to_whatsapp = f"whatsapp:{clean_phone}"

            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            data = {
                'From': twilio_from,
                'To': to_whatsapp,
                'Body': body_text,
            }

            try:
                response = requests.post(url, data=data, auth=(twilio_sid, twilio_token), timeout=20)
                status_code = response.status_code
                try:
                    res_json = response.json()
                except Exception:
                    res_json = {'raw_text': response.text}

                if 200 <= status_code < 300:
                    msg_id = res_json.get('sid', '')
                    return True, {
                        'status_code': status_code,
                        'message_id': msg_id,
                        'provider': 'twilio_whatsapp',
                        'data': res_json,
                    }, None
                else:
                    err_msg = res_json.get('message') or response.text or f"HTTP {status_code}"
                    return False, {
                        'status_code': status_code,
                        'data': res_json,
                    }, f"Twilio WhatsApp error ({status_code}): {err_msg}"
            except Exception as e:
                logger.error(f"Twilio WhatsApp dispatch exception: {e}")
                return False, None, f"Twilio WhatsApp error: {str(e)}"

        # 2. Check Meta WhatsApp credentials as fallback
        access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
        phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
        api_version = getattr(settings, 'WHATSAPP_API_VERSION', 'v21.0')

        if access_token and phone_number_id:
            meta_recipient = recipient_phone[1:] if recipient_phone.startswith('+') else recipient_phone
            meta_recipient = "".join(ch for ch in meta_recipient if ch.isdigit())

            url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }
            payload = {
                'messaging_product': 'whatsapp',
                'recipient_type': 'individual',
                'to': meta_recipient,
                'type': 'text',
                'text': {
                    'preview_url': False,
                    'body': body_text,
                }
            }

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=20)
                status_code = response.status_code
                try:
                    res_json = response.json()
                except Exception:
                    res_json = {'raw_text': response.text}

                if 200 <= status_code < 300:
                    messages = res_json.get('messages', [])
                    msg_id = messages[0].get('id') if messages else ''
                    return True, {
                        'status_code': status_code,
                        'message_id': msg_id,
                        'provider': 'meta_whatsapp',
                        'data': res_json,
                    }, None
                else:
                    error_info = res_json.get('error', {})
                    err_msg = error_info.get('message') or response.text or f"HTTP {status_code}"
                    return False, {
                        'status_code': status_code,
                        'data': res_json,
                    }, f"Meta WhatsApp error ({status_code}): {err_msg}"
            except Exception as e:
                return False, None, f"Meta WhatsApp error: {str(e)}"

        return False, None, "WhatsApp credentials not configured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN or Meta WhatsApp credentials missing)."
