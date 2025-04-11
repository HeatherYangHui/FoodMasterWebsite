from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile

@receiver(user_signed_up)
def create_user_profile(request, user, **kwargs):
    """
    Automatically create a Profile when a new user signs up via social login.
    Uses the user's email (or its prefix) as the default for profile fields.
    """
    # Use the part before the '@' in the email as the default full name/username.
    email = user.email or ""
    username_default = email.split('@')[0] if email else user.username

    # Check if the username is empty or whitespace and set it to the default.
    if not user.username or user.username.strip() == "":
        user.username = username_default
        user.save()

    # Create the Profile. You can set additional default fields as desired.
    Profile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': username_default,
            'bio': 'Please tell us about yourself!',
        }
    )