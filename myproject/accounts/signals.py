from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

@receiver(pre_save, sender=User)
def check_unique_email(sender, instance, **kwargs):
    if instance.email:
        email = instance.email.lower()
        exists = User.objects.filter(email__iexact=email).exclude(pk=instance.pk).exists()
        if exists:
            raise ValidationError("An account with this email already exists.")

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from shop.models import UserProfile
        UserProfile.objects.get_or_create(user=instance)

