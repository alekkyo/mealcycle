from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Profile, User


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Every user gets a profile (and so a trial) the moment they're created."""
    if created:
        Profile.objects.create(user=instance)
