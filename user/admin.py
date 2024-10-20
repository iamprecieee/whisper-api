from django.contrib.admin import register, ModelAdmin
from .models import User, UserOTP, JWTAccessToken


@register(User)
class UserAdmin(ModelAdmin):
    list_display = [
        "id",
        "email",
        "username",
        "is_email_verified",
        "is_username_set",
        "is_social_user",
        "is_2fa_enabled",
        "is_online",
        "is_otp_email_sent",
        "is_superuser",
        "is_staff",
        "created",
        "updated",
        "last_login",
    ]
    
    list_filter = [
        "id",
        "email",
        "is_email_verified",
        "is_username_set",
        "is_social_user",
        "is_2fa_enabled",
        "is_online",
        "is_superuser",
        "is_staff",
        "created",
    ]
    
    readonly_fields = ["password"]
    

@register(UserOTP)
class UserOTPAdmin(ModelAdmin):
    list_display = [
        "code",
        "otp_type",
        "user",
        "expiry",
    ]
    
    list_filter = [
        "otp_type",
        "user",
    ]
    

@register(JWTAccessToken)
class JWTAccessTokenAdmin(ModelAdmin):
    list_display = [
        "access_token",
        "user",
        "created"
    ]
    
    list_filter = [
        "user",
        "created"
    ]
