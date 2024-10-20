from typing import Any
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


class Error401View(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, exc):
        return Response(exc, status=status.HTTP_401_UNAUTHORIZED)


class Error404View(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, exc):
        return Response(exc, status=status.HTTP_404_NOT_FOUND)


class Error500View(APIView):
    def get(self, request, exc):
        return Response(exc, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
