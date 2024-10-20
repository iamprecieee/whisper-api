from django.db.models import TextChoices


class OTPTypeChoices(TextChoices):
    EMAIL = "EML", "Email"