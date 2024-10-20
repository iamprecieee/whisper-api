from django.urls import path
from .consumers import RoomConsumer


websocket_urlpatterns = [
    path("ws/chat/<str:room_id>/", RoomConsumer.as_asgi()),
] 