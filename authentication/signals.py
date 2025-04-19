from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile

# This signal is used to create a profile for the superuser when the superuser is created via the "createsuperuser" command
# ensures ID mismatch does not occur
@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if instance.is_superuser and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance, profileImage='https://i.ibb.co/C7zzTBM/depositphotos-137014128-stock-illustration-user-profile-icon.webp')
    elif hasattr(instance, 'profile'):
        instance.profile.save()
        