from django.core.management.base import BaseCommand
from apps.notifications.models import Trigger, NotificationTemplate


class Command(BaseCommand):
    help = 'Seed initial triggers and channel templates matching assignment specifications'

    def handle(self, *args, **options):
        initial_triggers = [
            {
                'name': 'Login',
                'event_key': 'user.login',
                'description': 'User signs in on the website.',
                'templates': {
                    'WHATSAPP': {
                        'name': 'Login WhatsApp',
                        'body': 'Welcome back, {{user.first_name}}! You logged in at {{event.time}}.',
                    },
                    'EMAIL': {
                        'name': 'Login Email',
                        'subject': 'You logged in successfully',
                        'body': 'Hi {{user.first_name}}, you logged into your account at {{event.time}}.',
                    },
                    'WEB_PUSH': {
                        'name': 'Login Web Push',
                        'title': 'Welcome back!',
                        'body': 'Welcome back, {{user.first_name}}! Great to see you again.',
                    },
                }
            },
            {
                'name': 'Logout',
                'event_key': 'user.logout',
                'description': 'User signs out.',
                'templates': {
                    'WHATSAPP': {
                        'name': 'Logout WhatsApp',
                        'body': 'Goodbye {{user.first_name}}, you logged out safely at {{event.time}}.',
                    },
                    'EMAIL': {
                        'name': 'Logout Email',
                        'subject': 'You logged out successfully',
                        'body': 'Hi {{user.first_name}}, you logged out of your account at {{event.time}}.',
                    },
                    'WEB_PUSH': {
                        'name': 'Logout Web Push',
                        'title': 'Goodbye!',
                        'body': 'You have safely logged out, {{user.first_name}}.',
                    },
                }
            },
            {
                'name': 'Not logged in 1 day',
                'event_key': 'user.inactive_1d',
                'description': 'User has not visited the website for 24 hours.',
                'templates': {
                    'WHATSAPP': {
                        'name': 'Inactive 1d WhatsApp',
                        'body': 'Hey {{user.first_name}}, check out what is new today!',
                    },
                    'EMAIL': {
                        'name': 'Inactive 1d Email',
                        'subject': 'We haven\'t seen you today!',
                        'body': 'Hi {{user.first_name}}, you have not visited the website for 24 hours. Check back in!',
                    },
                    'WEB_PUSH': {
                        'name': 'Inactive 1d Web Push',
                        'title': 'We miss you!',
                        'body': 'Come see what is happening today, {{user.first_name}}.',
                    },
                }
            },
            {
                'name': 'Not logged in 1 week',
                'event_key': 'user.inactive_1w',
                'description': 'User has not visited for 7 days.',
                'templates': {
                    'WHATSAPP': {
                        'name': 'Inactive 1w WhatsApp',
                        'body': 'We miss you, come back {{user.first_name}}!',
                    },
                    'EMAIL': {
                        'name': 'Inactive 1w Email',
                        'subject': 'It\'s been a week...',
                        'body': 'Hi {{user.first_name}}, it has been 7 days since your last visit. We miss you!',
                    },
                    'WEB_PUSH': {
                        'name': 'Inactive 1w Web Push',
                        'title': 'Come visit us again',
                        'body': 'It has been a week, {{user.first_name}}! Come visit us again.',
                    },
                }
            },
        ]

        for item in initial_triggers:
            trigger, created = Trigger.objects.get_or_create(
                event_key=item['event_key'],
                defaults={
                    'name': item['name'],
                    'description': item['description'],
                    'is_active': True,
                }
            )
            action = 'Created' if created else 'Already exists'
            self.stdout.write(self.style.SUCCESS(f"{action}: {trigger.name} ({trigger.event_key})"))

            # Create default templates for each channel
            for channel, tmpl_data in item.get('templates', {}).items():
                tmpl, tmpl_created = NotificationTemplate.objects.get_or_create(
                    trigger=trigger,
                    channel=channel,
                    defaults={
                        'name': tmpl_data.get('name', f"{trigger.name} - {channel}"),
                        'subject': tmpl_data.get('subject', ''),
                        'title': tmpl_data.get('title', ''),
                        'body': tmpl_data.get('body', ''),
                        'is_enabled': True,
                    }
                )
                t_action = 'Created template' if tmpl_created else 'Template exists'
                self.stdout.write(f"  -> {t_action}: [{channel}] {tmpl.name}")
