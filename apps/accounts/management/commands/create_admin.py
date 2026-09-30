from django.core.management.base import BaseCommand
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Create an admin user for the Notification System'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='admin@example.com')
        parser.add_argument('--password', type=str, default='AdminPass123!')
        parser.add_argument('--first-name', type=str, default='Admin')
        parser.add_argument('--last-name', type=str, default='User')
        parser.add_argument('--phone', type=str, default='+10000000000')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        phone = options['phone']

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Successfully created admin user: {email}"))
        else:
            user.role = User.Role.ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated existing user as admin: {email}"))
