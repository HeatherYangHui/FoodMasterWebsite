from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def single_timesince(value, now=None):

    if now is None:
        now = timezone.now()
    delta = now - value
    seconds = delta.total_seconds()
    
    if seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minutes ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hours ago"
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f"{days} days ago"
    elif seconds >= 31536000:
        years = int(seconds // 31536000)
        return f"{years} years ago"
    else:
        weeks = int(seconds // 604800)
        return f"{weeks} weeks ago"