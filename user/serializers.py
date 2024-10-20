from rest_framework.serializers import (
    ModelSerializer,
    CharField,
    EmailField,
    SerializerMethodField,
    Serializer,
    BooleanField
)
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from .models import User, UserOTP
from .utils import OTPEmail, WhisperSession
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from base64 import b32encode
from pyotp import TOTP
from django.db.transaction import atomic
from rest_framework_simplejwt.tokens import RefreshToken


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "is_email_verified",
            "is_username_set",
            "is_online",
            "created",
        ]
        read_only_fields = [
            "id",
            "email",
            "is_online",
            "is_email_verified",
            "is_username_set",
            "created"
        ]
        
class TOTPDeviceSerializer(ModelSerializer):
    class Meta:
        model = TOTPDevice
        fields = [
            "user",
            "name",
            "confirmed"
        ]
        
        
class RegisterSerializer(Serializer):
    id = CharField(read_only=True)
    email = EmailField()
    username = CharField(required=False)
    is_email_verified = BooleanField(read_only=True, default=False)
    is_username_set = BooleanField(read_only=True, default=False)
    message = CharField(read_only=True)
        
    def validate(self, data):
        username = data.get("username", None)
        email = data.get("email", None)
        if User.objects.filter(username=username).exists():
            raise ValidationError({"username error": "An account with this username already exists."})
        elif User.objects.filter(email=email).exists():
            raise ValidationError({"email error": "An account with this email already exists."})
        return data
    
    def save(self, **kwargs):
        return User.objects.create_user(**self.validated_data)
    
    def to_representation(self, instance):
        user_data = UserSerializer(instance).data
        user_data.pop("created")
        user_data.pop("is_online")
        user_data["message"] = "Check your email for a verification link."
        return user_data
    
    
class VerifyEmailBeginSerializer(Serializer):
    email = EmailField(write_only=True)
    message = CharField(read_only=True)
    
    def validate(self, data):
        email = data.get("email")
        self.user = User.objects.select_related("otp").filter(email=email).first()
        if not self.user:
            raise ValidationError({"email error": "No account is associated with this email."})
        elif self.user.is_otp_email_sent and timezone.now() < self.user.otp.expiry:
            raise ValidationError({"verification error": "A verification link has already been sent to this email address."})
        return data
        
    def save(self, **kwargs):
        OTPEmail(self.validated_data["email"], check_db=True).send_check_all()   
        return "Check your email for a verification link."
    
    def to_representation(self, instance):
        instance = {"message": instance}
        return instance
    
    
class VerifyEmailCompleteSerializer(Serializer):
    token = CharField(write_only=True)
    id = CharField(read_only=True)
    email = EmailField(read_only=True)
    username = CharField(read_only=True)
    is_email_verified = BooleanField(read_only=True)
    is_username_set = BooleanField(read_only=True, default=False)
    message = CharField(read_only=True)
    
    def validate(self, data):
        token = data.get("token")
        otp_email_instance = OTPEmail(token=token)
        self.user_otp = UserOTP.objects.select_related("user").filter(code=otp_email_instance.otp_code).first()
        if not self.user_otp:
            raise ValidationError({"otp error": "No account is associated with this OTP code."})
        self.user = self.user_otp.user
        if timezone.now() > self.user_otp.expiry:
            raise ValidationError({"otp error": "Code is expired. Request a new verification link."})
        return data
    
    def save(self, **kwargs):
        self.user.is_email_verified = True
        self.user.save(update_fields=["is_email_verified"])
        self.user_otp.delete()
        
        session_instance = WhisperSession(self.context["request"])
        session_instance.add(user_email=self.user.email)
        return self.user
    
    def to_representation(self, instance):
        user_data = UserSerializer(instance).data
        user_data.pop("is_online")
        user_data.pop("created")
        user_data["message"] = "Proceed to 2FA setup."
        return user_data
    
    
class TOTPDeviceCreateSerializer(Serializer):
    user = CharField(read_only=True)
    name = CharField(read_only=True)
    email = EmailField(required=False)
    confirmed = BooleanField(read_only=True, default=False)
    
    def validate(self, data):
        session_instance = WhisperSession(self.context["request"])
        self.email = session_instance.get_email()
        if not self.email:
            self.email = data.get("email")
            session_instance.add(user_email=self.email)
        self.user = User.objects.filter(email=self.email).first()
        if not self.user:
            raise ValidationError({"email error": "No account is associated with this email."})
        if not self.user.is_email_verified:
            raise ValidationError({"email error": "This account has not been verified. Check your email for a verification link."})
        if TOTPDevice.objects.filter(user=self.user).exists():
            raise ValidationError({"2FA error": "TOTP device already exists for this account."})
        return data
    
    def save(self, **kwargs):
        return TOTPDevice.objects.create(user=self.user, name=self.email, confirmed=False)
    
    def to_representation(self, instance):
        return TOTPDeviceSerializer(instance).data
        

class QRCodeDataSerializer(Serializer):
    otpauth_url = CharField(read_only=True)
    email = EmailField(required=False)
    
    def validate(self, data):
        session_instance = WhisperSession(self.context["request"])
        self.email = session_instance.get_email()
        if not self.email:
            self.email = data.get("email")
            session_instance.add(user_email=self.email)
        self.device = TOTPDevice.objects.filter(user__email=self.email, confirmed=False).first()
        if not self.device:
            raise ValidationError({"2FA error": "No unconfirmed TOTP device is associated with this email."})
        return data
    
    def save(self, **kwargs):
        return self.device.config_url
    
    
class VerifyTOTPDeviceSerializer(Serializer):
    otp_token = CharField(write_only=True)
    user = CharField(read_only=True)
    name = CharField(read_only=True)
    confirmed = BooleanField(read_only=True)
    message = CharField(read_only=True)
    
    def validate(self, data):
        session_instance = WhisperSession(self.context["request"])
        email = session_instance.get_email()
        self.otp_token = data.get("otp_token")
        self.device = TOTPDevice.objects.select_related("user").filter(user__email=email, confirmed=False).first()
        if not self.device:
            raise ValidationError({"2FA error": "No unconfirmed TOTP device is associated with this email."})
        return data
    
    def save(self, **kwargs):
        secret_key = b32encode(self.device.bin_key).decode()
        totp = TOTP(secret_key)
        if not totp.verify(self.otp_token):
            raise ValidationError({"2FA error": "TOTP token is invalid."})
        with atomic():
            self.device.confirmed = True
            self.device.save()
            self.device.user.is_2fa_enabled = True
            self.device.user.save()
        return self.device
    
    def to_representation(self, instance):
        result = TOTPDeviceSerializer(instance).data
        result["message"] = "TOTP Device verified successfully. Proceed to login."
        return result
    
    
class LoginSerializer(Serializer):
    email = EmailField(write_only=True)
    
    def validate(self, data):
        self.email = data.get("email")
        user = User.objects.filter(email=self.email).first() 
        if not user:
            raise ValidationError({"email error": "No account is associated with this email."})
        if not user.is_2fa_enabled:
            raise AuthenticationFailed("2FA setup must be completed before login.")
        return data
    
    def save(self, **kwargs):
        session_instance = WhisperSession(self.context["request"])
        session_instance.add(user_email=self.email)
        
        
class VerifyTOTPSerializer(Serializer):
    otp_token = CharField(write_only=True)
    id = CharField(read_only=True)
    email = CharField(read_only=True)
    access = CharField(read_only=True)
    refresh = CharField(read_only=True)
    
    def validate(self, data):
        self.session_instance = WhisperSession(self.context["request"])
        email = self.session_instance.get_email()
        self.otp_token = data.get("otp_token")
        self.device = TOTPDevice.objects.select_related("user").filter(user__email=email, confirmed=True).first()
        if not self.device:
            raise ValidationError({"2FA error": "No confirmed TOTP device is associated with this email."})
        return data
    
    def save(self, **kwargs):
        validated_data = self.validated_data
        secret_key = b32encode(self.device.bin_key).decode()
        totp = TOTP(secret_key)
        if not totp.verify(self.otp_token):
            raise ValidationError({"2FA error": "TOTP token is invalid."})
        refresh_token = RefreshToken.for_user(self.device.user)
        access_token = refresh_token.access_token
        with atomic():
            self.device.user.access_token.access_token = access_token
            self.device.user.access_token.save(update_fields=["access_token"])
            self.session_instance.add(user_refresh_token=str(refresh_token))
        validated_data.clear()
        validated_data["id"] = self.device.user.id
        validated_data["email"] = self.device.user.email
        validated_data["access"] = str(access_token)
        validated_data["refresh"] = str(refresh_token)
        return validated_data
    
    def to_representation(self, instance):
        return instance
    
    
class RefreshTokenSerializer(Serializer):
    id = CharField(read_only=True)
    email = CharField(read_only=True)
    access = CharField(read_only=True)
    refresh = CharField(read_only=True)
    
    def save(self, **kwargs):
        request = self.context["request"]
        new_refresh_token = RefreshToken.for_user(request.user)
        with atomic():
            session_instance = WhisperSession(self.context["request"])
            session_instance.remove_refresh_token()
            session_instance.add(user_refresh_token=str(new_refresh_token))
            request.user.access_token.access_token = new_refresh_token.access_token
            request.user.access_token.save(update_fields=["access_token"])
        validated_data = self.validated_data
        validated_data.clear()
        validated_data["id"] = request.user.id
        validated_data["email"] = request.user.email
        validated_data["access"] = str(new_refresh_token.access_token)
        validated_data["refresh"] = str(new_refresh_token)
        return validated_data

    def to_representation(self, instance):
        return instance
    
    