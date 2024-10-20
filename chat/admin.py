from django.contrib.admin import register, ModelAdmin, StackedInline

from .models import Room, Message


@register(Room)
class RoomAdmin(ModelAdmin):
    list_display = ["id", "room_name", "creator", "created"]
    list_filter = ["id", "created"]
    filter_horizontal = ["users"]


@register(Message)
class MessageAdmin(ModelAdmin):
    list_display = [
        "id",
        "message_format",
        "text_content",
        "image_content",
        "audio_content",
        "video_content",
        "is_reply",
        "previous_message_content",
        "previous_message_id",
        "previous_sender",
        "sender",
        "room",
        "created",
        "updated",
    ]
    list_filter = ["id", "sender", "created", "updated"]