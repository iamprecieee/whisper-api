import qrcode.constants
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    RegisterSerializer,
    VerifyEmailBeginSerializer,
    VerifyEmailCompleteSerializer,
    TOTPDeviceCreateSerializer,
    QRCodeDataSerializer,
    VerifyTOTPDeviceSerializer,
    LoginSerializer,
    VerifyTOTPSerializer,
    RefreshTokenSerializer,
)
from rest_framework.exceptions import ValidationError, AuthenticationFailed
import qrcode
from io import BytesIO
from .utils import PNGRenderer
from rest_framework.renderers import BrowsableAPIRenderer
from django.shortcuts import redirect
from drf_spectacular.utils import extend_schema
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from social_django.utils import psa
from .social_authentication import complete_social_authentication
from social_core.actions import do_auth
from django.contrib.auth import REDIRECT_FIELD_NAME
from rest_framework.permissions import AllowAny, IsAuthenticated

   

class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    @extend_schema(
        operation_id="v1_register",
        tags=["auth_v1"]
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        try:
            if serializer.is_valid(raise_exception=True):
                user_data = serializer.save()
                response_data = self.serializer_class(user_data).data
                return Response(response_data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(str(e))
        
        
    
class VerifyEmailBeginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyEmailBeginSerializer

    @extend_schema(
        operation_id="v1_verify_email_begin",
        tags=["auth_v1"]
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        try:
            if serializer.is_valid(raise_exception=True):
                response_data = serializer.save()
                return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(str(e))
        
        
class VerifyEmailCompleteView(APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyEmailCompleteSerializer

    @extend_schema(
        operation_id="v1_verify_email_complete",
        tags=["auth_v1"]
    )
    def post(self, request, token):
        serializer = self.serializer_class(data={"token": token}, context={"request": request})
        try:
            if serializer.is_valid(raise_exception=True):
                user_data = serializer.save()
                response_data = self.serializer_class(user_data).data
                return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(str(e))


class TOTPDeviceCreateView(APIView):
    permission_classes = [AllowAny]
    serializer_class = TOTPDeviceCreateSerializer

    @extend_schema(
        operation_id="v1_create_totp_device",
        tags=["auth_v1"]
    )
    def post(self, request):
        serializer = self.serializer_class(data={"dummy": "dummy"}, context={"request":request})
        try:
            if serializer.is_valid(raise_exception=True):
                device_data = serializer.save()
                response_data = self.serializer_class(device_data).data
                return Response(response_data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(str(e))
        
        
class GetQRCodeView(APIView):
    permission_classes = [AllowAny]
    serializer_class = QRCodeDataSerializer

    @extend_schema(
        operation_id="v1_get_qrcode",
        tags=["auth_v1"]
    )
    def post(self, request):
        serializer = self.serializer_class(data={"dummy": "dummy"}, context={"request":request})
        try:
            if serializer.is_valid(raise_exception=True):
                otpauth_url = serializer.save()
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.ERROR_CORRECT_H,
                    box_size=10,
                    border=4,
                )
                qr.add_data(otpauth_url)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color=(169, 56, 56), back_color=(252, 217, 157))
                image_buffer = BytesIO()
                img.save(image_buffer)
                image_buffer.seek(0)
                return Response(image_buffer.getvalue(), content_type="image/png", status=status.HTTP_200_OK)
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(str(e))
        
    def finalize_response(self, request, response, *args, **kwargs):
        if response.content_type == "image/png":
            response.accepted_renderer = PNGRenderer()
            response.accepted_media_type = PNGRenderer.media_type
            response.renderer_context = {}
        else:
            response.accepted_renderer = BrowsableAPIRenderer()
            response.accepted_media_type = BrowsableAPIRenderer.media_type
            response.renderer_context = {
                "response": response.data,
                "view": self,
                "request": request
            }
        for key, value in self.headers.items():
            response[key] = value
        return response
    
    
        
class VerifyTOTPDeviceView(APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyTOTPDeviceSerializer

    @extend_schema(
        operation_id="v1_verify_totp_device",
        tags=["auth_v1"]
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request":request})
        try:
            if serializer.is_valid(raise_exception=True):
                device_data = serializer.save()
                response_data = self.serializer_class(device_data).data
                return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(str(e))
        
        
class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    @extend_schema(
        operation_id="v1_login",
        tags=["auth_v1"],
        request=LoginSerializer
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request":request})
        try:
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return redirect("user:verify-totp")
        except ValidationError as e:
            raise e
        except AuthenticationFailed as e:
            raise AuthenticationFailed(str(e))
        except Exception as e:
            raise Exception(str(e))
        
        
class VerifyTOTPView(APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyTOTPSerializer
    
    @extend_schema(
        operation_id="v1_verify_totp",
        tags=["auth_v1"]
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request":request})
        try:
            if serializer.is_valid(raise_exception=True):
                user_data = serializer.save()
                response_data = self.serializer_class(user_data).data
                return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(str(e))
        
        
class RefreshView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RefreshTokenSerializer

    @extend_schema(
        operation_id="v1_refresh",
        tags=["auth_v1"]
    )
    def post(self, request):
        serializer = self.serializer_class(context={"request": request})
        try:
            data = serializer.save()
            response_data = self.serializer_class(data).data
            return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(str(e))
        

@method_decorator([csrf_exempt, never_cache, psa("user:social-complete")], name="get")
class SocialAuthenticationBeginView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        operation_id="v1_social_auth_begin",
        tags=["auth_v1"],
        request=None,
        responses=None
    )
    def get(self, request, backend):
        try:
            return do_auth(request.backend, redirect_name=REDIRECT_FIELD_NAME)
        except AuthenticationFailed as e:
            raise AuthenticationFailed(str(e))
        except Exception as e:
            raise Exception(str(e))
    

@method_decorator([csrf_exempt, never_cache, psa("user:social-complete")], name="get")
class SocialAuthenticationCompleteView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        operation_id="v1_social_auth_complete",
        tags=["auth_v1"],
        request=None,
        responses=None
    )
    def get(self, request, backend):
        try:
            return complete_social_authentication(request, backend)
        except AuthenticationFailed as e:
            raise AuthenticationFailed(str(e))
        except Exception as e:
            raise Exception(str(e))