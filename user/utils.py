from nanoid import generate
from .choices import OTPTypeChoices
from pyotp import TOTP, random_base32
from django.core import signing
from django.core.mail import send_mail
from django.conf import settings
from smtplib import SMTPException
from rest_framework.exceptions import ValidationError
from django.db.transaction import atomic
from rest_framework.renderers import BaseRenderer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.sessions.exceptions import SessionInterrupted


def generate_username():
    return f"user-{generate(size=10)}"


def generate_access_token():
    return f"access-{generate(size=10)}"
    
    
class OTPEmail:
    def __init__(
        self,
        email=None,
        otp_type=OTPTypeChoices.EMAIL,
        token=None,
        check_db=False,
    ):
        from .models import User
        
        self.email=email
        self.otp_type = otp_type
        self.token = token
        self.check_db = check_db
        self.otp_code = None
        self.user = None
        self.user_id = None
        
        if self.check_db:
            user = User.objects.filter(email=self.email).first()
            if user:
                self.user = user
        elif self.token:
            self.decode_signed_token()
            self.user = User.objects.filter(id=self.user_id).first()
        
    def generate_otp_code(self):
        from .models import UserOTP
        
        if self.user:
            self.otp_code = TOTP(random_base32(), digits=6).now()
            with atomic():
                if hasattr(self.user, "otp"):
                    self.user.otp.delete()
                UserOTP.objects.create(code=self.otp_code, otp_type=self.otp_type, user=self.user)
            
    def generate_signed_token(self):
        self.token = signing.dumps((self.otp_code, self.user.id))
        
    def send_otp_email(self):
        current_host = settings.CURRENT_HOST
        sender_email = settings.SENDER_EMAIL
        url_path = "verify-email"
        operation_message = "verify your email"
        subject = "Email Verification"

        html_message = f"""
            <html>
                <body>
                    <p>
                        Click this link to {operation_message}:<br>
                        <a href='http://{current_host}/api/v1/user/{url_path}/complete/{self.token}/'>{url_path.replace('-', ' ').capitalize()}</a>
                    </p>
                </body>
            </html>
        """
        try:
            send_mail(
                subject=subject,
                message=html_message,
                from_email=sender_email,
                recipient_list=[self.email],
                html_message=html_message,
                fail_silently=False,
                auth_user=settings.EMAIL_HOST_USER,
                auth_password=settings.EMAIL_HOST_PASSWORD
            )
        except SMTPException as e:
            raise Exception({"smtp error": f"{e}"})
        except Exception as e:
            raise Exception({"untracked error": f"{e}"})
        
    def decode_signed_token(self):
        try:
            self.otp_code, self.user_id = signing.loads(self.token)
        except signing.BadSignature:
            raise ValidationError({"otp error": "Invalid OTP token detected. Request a new verification link."})
        
    def send_check_all(self):
        with atomic():
            self.generate_otp_code()
            self.generate_signed_token()
            self.send_otp_email()
            self.user.is_otp_email_sent = True
            self.user.save(update_fields=["is_otp_email_sent"])
            

class PNGRenderer(BaseRenderer):
    media_type = "image/png"
    format = "png"
    charset = None
    render_style = "binary"
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data
    
    
class WhisperSession:
    def __init__(self, request):
        self.session = request.session
        session_email = self.session.get(settings.EMAIL_SESSION_ID)
        if not session_email:
            session_email = self.session[settings.EMAIL_SESSION_ID] = {}
        self.session_email = session_email
        session_refresh_token = self.session.get(settings.REFRESH_SESSION_ID)
        if not session_refresh_token:
            session_refresh_token = self.session[settings.REFRESH_SESSION_ID] = {}
        self.session_refresh_token = session_refresh_token
        
    def save(self):
        self.session.modified = True
        
    def add(self, user_email=None, user_refresh_token=None):
        if user_email:
            self.session_email["email"] = user_email
        elif user_refresh_token:
            self.session_refresh_token["refresh"] = user_refresh_token
        self.save()
        
    def get_email(self):
        return self.session_email.get("email")
    
    def get_refresh_token(self):
        return self.session_refresh_token.get("refresh")
    
    def remove_email(self):
        if self.session_email.get("email"):
            del self.session_email["email"]
            self.save()
            
    def remove_refresh_token(self):
        if self.session_refresh_token.get("refresh"):
            existing_refresh_token = self.get_refresh_token()
            try:
                validated_refresh_token = RefreshToken(existing_refresh_token)
                if settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]:
                    if settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"]:
                        try:
                            validated_refresh_token.blacklist()
                        except AttributeError:
                            pass

                    validated_refresh_token.set_jti()
                    validated_refresh_token.set_exp()
                    validated_refresh_token.set_iat()

                del self.session_refresh_token["refresh"]
                self.save()
            except (TokenError, SessionInterrupted):
                self.session_refresh_token = {}
                self.save()