from django.urls import path
from .views import (
    RoomListView,
    RoomHTMLView,
)


app_name = "chat"
urlpatterns = [
    path("room-list/", RoomListView.as_view(), name="room-list"),
    path("home/<str:room_id>/", RoomHTMLView.as_view(), name="room-home"),
]
