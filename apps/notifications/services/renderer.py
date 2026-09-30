import re
from datetime import datetime
from django.utils import timezone


class TemplateRenderer:
    """
    Safely replaces template variables in notification strings.
    Supported variables:
      {{user.first_name}}
      {{user.last_name}}
      {{user.email}}
      {{user.phone}}
      {{event.time}}
    No arbitrary code execution allowed. Unknown variables remain untouched.
    """

    ALLOWED_VARIABLES = {
        'user.first_name',
        'user.last_name',
        'user.email',
        'user.phone',
        'event.time',
    }

    VARIABLE_REGEX = re.compile(r'\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}')

    @classmethod
    def render(cls, template_string: str, user, event_time=None) -> str:
        if not template_string:
            return ""

        if event_time is None:
            event_time = timezone.now()

        formatted_time = event_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(event_time, 'strftime') else str(event_time)

        context = {
            'user.first_name': getattr(user, 'first_name', '') or '',
            'user.last_name': getattr(user, 'last_name', '') or '',
            'user.email': getattr(user, 'email', '') or '',
            'user.phone': getattr(user, 'phone', '') or '',
            'event.time': formatted_time,
        }

        def _replace_match(match):
            var_name = match.group(1).strip()
            if var_name in cls.ALLOWED_VARIABLES:
                return str(context.get(var_name, ''))
            return match.group(0)

        return cls.VARIABLE_REGEX.sub(_replace_match, template_string)

    @classmethod
    def extract_variables(cls, template_string: str) -> list:
        if not template_string:
            return []
        matches = cls.VARIABLE_REGEX.findall(template_string)
        return sorted(list(set(m.strip() for m in matches if m.strip() in cls.ALLOWED_VARIABLES)))
