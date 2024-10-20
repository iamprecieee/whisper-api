from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin
)
from django.db.models import (
    Model,
    EmailField,
    CharField,
    BooleanField,
    DateTimeField,
    OneToOneField,
    CASCADE,
    
)
from .utils import generate_username, generate_access_token
from .choices import OTPTypeChoices
from nanoid import generate
from django.utils import timezone
from datetime import timedelta


class WhisperUserManager(BaseUserManager):
    def _create_user(self, **kwargs):
        email = kwargs.pop("email")
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        normalized_email = self.normalize_email(email)
        if any([not username, username == ""]):
            username = generate_username()
        kwargs.setdefault("username", username)
        user = self.model(email=normalized_email, **kwargs)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, **kwargs):
        kwargs.setdefault("is_email_verified", True)
        kwargs.setdefault("is_username_set", True)
        kwargs.setdefault("is_2fa_enabled", True)
        kwargs.setdefault("is_superuser", True)
        kwargs.setdefault("is_staff", True)
        return self._create_user(**kwargs)
    
    def create_user(self, **kwargs):
        return self._create_user(**kwargs)
    

class User(AbstractBaseUser, PermissionsMixin):
    id = CharField(max_length=21, primary_key=True, editable=False, unique=True, default=generate)
    email = EmailField(max_length=120, blank=False, unique=True, db_index=True)
    username = CharField(max_length=120, blank=True, unique=True, db_index=True)
    is_email_verified = BooleanField(default=False, db_index=True)
    is_username_set = BooleanField(default=False)
    is_social_user = BooleanField(default=False, db_index=True)
    is_2fa_enabled = BooleanField(default=False)
    is_online = BooleanField(default=False)
    is_otp_email_sent = BooleanField(default=False, db_index=True)
    is_superuser = BooleanField(default=False)
    is_staff = BooleanField(default=False)
    is_test_user = BooleanField(default=False, db_index=True)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    last_login = DateTimeField(auto_now=True)
    
    objects = WhisperUserManager()
    
    USERNAME_FIELD = "email"
    
    class Meta:
        db_table = "user"
        ordering = ["-created"]
        
    def __str__(self):
        return self.username
    
    
class UserOTP(Model):
    code = CharField(max_length=6, unique=True, editable=False, db_index=True)
    otp_type = CharField(
        max_length=3,
        blank=True,
        choices=OTPTypeChoices.choices,
        default=OTPTypeChoices.EMAIL,
    )
    user = OneToOneField(User, related_name="otp", on_delete=CASCADE)
    expiry = DateTimeField(
        editable=False, db_index=True, default=timezone.now() + timedelta(minutes=5)
    )

    class Meta:
        db_table = "user_otp"
        ordering = ["-expiry"]

    def __str__(self):
        return f"{self.user.username}'s OTP code"


class JWTAccessToken(Model):
    access_token = CharField(
        max_length=1024,
        unique=True,
        db_index=True,
    )
    user = OneToOneField(User, related_name="access_token", on_delete=CASCADE)
    created = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_jwt_access_token"
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user.username}'s JWT access token"

    def save(self, *args, **kwargs) -> None:
        if not self.access_token:
            self.access_token = generate_access_token()
        return super().save(*args, **kwargs)