from datetime import datetime
from django.test import TestCase
from apps.accounts.models import User
from apps.notifications.services.renderer import TemplateRenderer


class TemplateRendererTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='alice@example.com',
            first_name='Alice',
            last_name='Wonderland',
            phone='+15551234567',
            password='Password123!',
        )
        self.fixed_time = datetime(2026, 9, 30, 12, 0, 0)

    def test_variable_replacement(self):
        raw = "Hello {{user.first_name}} {{user.last_name}}, your email is {{user.email}} and phone is {{user.phone}} at {{event.time}}."
        rendered = TemplateRenderer.render(raw, self.user, self.fixed_time)
        expected = "Hello Alice Wonderland, your email is alice@example.com and phone is +15551234567 at 2026-09-30 12:00:00."
        self.assertEqual(rendered, expected)

    def test_unknown_variable_is_untouched(self):
        raw = "Hello {{user.first_name}}, system version is {{system.version}} and code is {{code.run()}}."
        rendered = TemplateRenderer.render(raw, self.user, self.fixed_time)
        expected = "Hello Alice, system version is {{system.version}} and code is {{code.run()}}."
        self.assertEqual(rendered, expected)

    def test_empty_template(self):
        self.assertEqual(TemplateRenderer.render("", self.user), "")
        self.assertEqual(TemplateRenderer.render(None, self.user), "")

    def test_extract_variables(self):
        raw = "Hi {{user.first_name}}, logged in at {{event.time}} with {{fake.var}}"
        vars_found = TemplateRenderer.extract_variables(raw)
        self.assertEqual(vars_found, ['event.time', 'user.first_name'])
