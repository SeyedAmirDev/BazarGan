from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, Profile


@receiver(post_save, sender=User)
def save_profile(sender, instance, created, **kwargs):
    """
    A signal receiver triggered after a User model is saved and
    Automatically creates a Profile for newly registered users.
    """
    if created:
        Profile.objects.create(user=instance, pk=instance.pk)
