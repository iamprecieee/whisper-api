from rest_framework.test import APITransactionTestCase
from django.urls import reverse
from .models import User, UserOTP
from .utils import OTPEmail
from django_otp.plugins.otp_totp.models import TOTPDevice


class RegisterVerifyEmailTestCase(APITransactionTestCase):
        
    def setUp(self):
        self.register = reverse("user:register")
        self.verify_begin = reverse("user:verify-email-begin")
        self.new_user = User.objects.create_user(
            email="admin@gmail.com",
            username="admin",
            is_otp_email_sent=False,
            is_test_user=True
        )
        
    def test_register_success(self):
        response = self.client.post(self.register,
                                    data={"email": "emmypresh777@gmail.com"})
        for item in ["email", "username", "message"]:
            self.assertIn(item, response.data)
        user = User.objects.filter(email=response.data["email"]).first()
        self.assertTrue(user.is_otp_email_sent)
            
    def test_verify_begin_success(self):
        response = self.client.post(self.verify_begin,
                                    data={"email": "admin@gmail.com"})
        self.assertEqual("Check your email for a verification link.", response.data)
        user = User.objects.filter(email=self.new_user.email).first()
        self.assertTrue(user.is_otp_email_sent)
        
    def test_verify_complete_success(self):
        self.client.post(self.verify_begin,
                                    data={"email": "admin@gmail.com"})
        otp_code = UserOTP.objects.filter(user=self.new_user).first().code
        otp_email_instance = OTPEmail(email=self.new_user.email, check_db=True)
        otp_email_instance.otp_code = otp_code
        otp_email_instance.generate_signed_token()
        response = self.client.post(reverse("user:verify-email-complete",
                                            kwargs={"token": otp_email_instance.token}))
        for item in ["id", "email", "username", "message"]:
            self.assertIn(item, response.data)
        user = User.objects.filter(email=self.new_user.email).first()
        self.assertTrue(user.is_email_verified)
        
        
class TOTPCreateVerifyTestCase(APITransactionTestCase):
    def setUp(self):
        self.device_create = reverse("user:create-totp-device")
        self.qrcode = reverse("user:get-qr-code")
        self.verify_device = reverse("user:verify-totp-device")
        self.new_user = User.objects.create_user(
            email="admin@gmail.com",
            username="admin",
            is_otp_email_sent=False,
            is_test_user=True
        )
        
        self.client.post(reverse("user:verify-email-begin"),
                                    data={"email": "admin@gmail.com"})
        otp_code = UserOTP.objects.filter(user=self.new_user).first().code
        otp_email_instance = OTPEmail(email=self.new_user.email, check_db=True)
        otp_email_instance.otp_code = otp_code
        otp_email_instance.generate_signed_token()
        self.client.post(reverse("user:verify-email-complete",
                                            kwargs={"token": otp_email_instance.token}))

        
    def test_create_device_success(self):
        response = self.client.post(self.device_create)
        for item in ["user", "name", "confirmed"]:
            self.assertIn(item, response.data)
        self.assertFalse(response.data["confirmed"])
        
    def test_get_qrcode_success(self):
        self.client.post(self.device_create)
        response = self.client.post(self.qrcode)
        self.assertTrue(type(response.data) == bytes)