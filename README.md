# Notification System — Backend API & Worker

Event-driven notification dispatch backend built with **Django REST Framework**, **Celery**, **Redis**, and **PostgreSQL**.

## Features
- **Async Queues**: Decoupled background dispatch via Celery & Redis.
- **Channels**: WhatsApp (Twilio Sandbox), Email (Resend), Web Push (OneSignal).
- **Idempotency**: Strict database constraints prevent duplicate notifications.
- **Exponential Backoff**: Automated retries for transient provider errors.
- **Admin APIs**: Full CRUD and test send for triggers and channel templates.

## Admin Credentials
- **Email**: `admin@example.com`
- **Password**: `NotifyAdmin@2026`

## Local Setup
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows (or source venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_triggers
celery -A config worker -l info -P solo
python manage.py runserver 0.0.0.0:8000
```

## Production Deployment (Render)
- **Build Command**: `pip install -r requirements.txt && python manage.py migrate && python manage.py seed_triggers`
- **Web Service Start Command**: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- **Celery Worker Start Command**: `celery -A config worker -l info`
