from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, JWTAccessToken
from .utils import OTPEmail


@receiver(post_save, sender=User)
def send_otp_email(sender, instance, created, **kwargs):
    try:
        if all([created, not instance.is_superuser, not instance.is_test_user]):
            JWTAccessToken.objects.create(user=instance)
            if not instance.is_social_user:
                OTPEmail(instance.email, check_db=True).send_check_all()
    except Exception as e:
        raise Exception(f"{e}")