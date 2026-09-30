import os
import dj_database_url
from .base import *

DEBUG = False

allowed = os.environ.get('ALLOWED_HOSTS', '')
if allowed:
    ALLOWED_HOSTS = [h.strip() for h in allowed.split(',') if h.strip()]
else:
    render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    ALLOWED_HOSTS = [render_host] if render_host else ['*']

database_url = os.environ.get('DATABASE_URL')
if database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
