from social_core.utils import user_is_authenticated, user_is_active, partial_pipeline_data
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from django.shortcuts import redirect
from .utils import WhisperSession
from .serializers import UserSerializer


def complete_social_authentication(request, backend):
    backend = request.backend
    user = request.user
    
    # Check if user is authenticated
    is_user_authenticated = user_is_authenticated(user)
    user = user if is_user_authenticated else None
    
    # Complete partial authentication or perform a full one
    partial = partial_pipeline_data(backend, user)
    if partial:
        user = backend.continue_pipeline(partial)
        backend.clean_partial_pipeline(partial.token)
    else:
        user = backend.complete(user=user)
        
    user_model = backend.strategy.storage.user.user_model()
    if user and not isinstance(user, user_model):
        return Response("Provided 'user' is not a valid User object.", status=status.HTTP_400_BAD_REQUEST)
        
    if user:
        if user_is_active(user):
            is_new = getattr(user, "is_new", False)
            if is_new:
                user_data = UserSerializer(user).data
                user_data.pop("is_online")
                user_data.pop("created")
                user_data["message"] = "Proceed to 2FA setup."
                return Response(user_data, status=status.HTTP_201_CREATED)
            else:
                if not user.is_2fa_enabled:
                    raise AuthenticationFailed("2FA setup must be completed before login.")
                else:
                    session_instance = WhisperSession(request)
                    session_instance.add(user_email=user.email)
                    return redirect("user:verify-totp")
        else:      
            return Response("This account is inactive.", status=status.HTTP_400_BAD_REQUEST)