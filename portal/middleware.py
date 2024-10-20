from django.urls import resolve, reverse
from rest_framework.permissions import AllowAny
from user.models import JWTAccessToken
from django.shortcuts import redirect


class ClearAuthenticationHeaderMiddleware:
    @staticmethod
    def get_permission_class_app_name(request):
        resolver_match = resolve(request.path_info)
        app_names = resolver_match.app_names
        view_function = resolver_match.func
        view_class = getattr(view_function, "view_class", None)
        permission_classes = getattr(view_class, "permission_classes", [])
        return permission_classes, app_names
    
    @staticmethod
    def get_header_auth_token(request):
        token  = None
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        return token
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if not self.process_request(request):
            return redirect(reverse("error-401", kwargs={"exc": "Session expired. Kindly login again."}))
        return self.get_response(request)
        
    def process_request(self, request):
        permission_classes, app_names = self.get_permission_class_app_name(request)
        token = self.get_header_auth_token(request)
        if any([AllowAny in permission_classes, "admin" in app_names]):
            request.META.pop("HTTP_AUTHORIZATION", "")
            return True
        elif token and not JWTAccessToken.objects.filter(access_token=token).exists():
            return False
        return True