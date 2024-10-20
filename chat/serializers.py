from django.contrib.auth import get_user_model
from rest_framework.serializers import ModelSerializer, SerializerMethodField, ListField
from rest_framework.exceptions import ValidationError
from .models import Room, Message
from django.utils.dateformat import format
from asgiref.sync import sync_to_async


User = get_user_model()


class MessageSerializer(ModelSerializer):
    sender = SerializerMethodField()
    room = SerializerMethodField()
    username = SerializerMethodField()
    created = SerializerMethodField()
    date = SerializerMethodField()
    time = SerializerMethodField()
    previous_sender_username = SerializerMethodField()
    previous_message_type = SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "message_format",
            "text_content",
            "image_content",
            "audio_content",
            "video_content",
            "is_reply",
            "previous_message_content",
            "previous_message_type",
            "previous_message_id",
            "previous_sender_username",
            "sender",
            "room",
            "created",
            "date",
            "time",
            "username",
        ]
        read_only_fields = [
            "id",
            "sender",
            "room",
            "created",
            "date",
            "time"
        ]

    def get_sender(self, obj):
        return obj.sender.id

    def get_room(self, obj):
        return obj.room.id
        
    def get_username(self, obj):
        return obj.sender.username
    
    def get_previous_sender_username(self, obj):
        return User.objects.filter(id=obj.previous_sender).first().username if obj.previous_sender else None
    
    def get_previous_message_type(self, obj):
        return Message.objects.filter(id=obj.previous_message_id).first().message_format if obj.previous_message_id else None
    
    def get_created(self, obj):
        return format(obj.created, "M. d, Y. P")
    
    def get_date(self, obj):
        return format(obj.created, "M. d, Y")
    
    def get_time(self, obj):
        return format(obj.created, "P")
    
    
class AsyncMessageSerializer(ModelSerializer):
    sender = SerializerMethodField()
    room = SerializerMethodField()
    username = SerializerMethodField()
    created = SerializerMethodField()
    date = SerializerMethodField()
    time = SerializerMethodField()
    previous_sender_username = SerializerMethodField()
    previous_message_type = SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "message_format",
            "text_content",
            "image_content",
            "audio_content",
            "video_content",
            "is_reply",
            "previous_message_content",
            "previous_message_type",
            "previous_message_id",
            "previous_sender_username",
            "sender",
            "room",
            "created",
            "date",
            "time",
            "username",
        ]
        read_only_fields = [
            "id",
            "sender",
            "room",
            "created",
            "date",
            "time"
        ]

    @sync_to_async
    def get_sender(self, obj):
        return obj.sender.id

    @sync_to_async
    def get_room(self, obj):
        return obj.room.id
        
    @sync_to_async
    def get_username(self, obj):
        return obj.sender.username
    
    @sync_to_async
    def get_previous_sender_username(self, obj):
        return User.objects.filter(id=obj.previous_sender).first().username if obj.previous_sender else None
    
    @sync_to_async
    def get_previous_message_type(self, obj):
        return Message.objects.filter(id=obj.previous_message_id).first().message_format if obj.previous_message_id else None
    
    @sync_to_async
    def get_created(self, obj):
        return format(obj.created, "M. d, Y. P")
    
    @sync_to_async
    def get_date(self, obj):
        return format(obj.created, "M. d, Y")
    
    @sync_to_async
    def get_time(self, obj):
        return format(obj.created, "P")
    
    
class RoomSerializer(ModelSerializer):
    users = SerializerMethodField()
    user_ids = ListField(write_only=True)

    class Meta:
        model = Room
        fields = ["id", "room_name", "users", "creator", "created", "user_ids"]
        read_only_fields = ["id", "creator", "created"]

    def create(self, validated_data):
        users_data = validated_data.pop("user_ids")
        current_user = self.context.get("user")
        validated_data["creator"] = current_user
        new_room = Room.objects.create(**validated_data)

        if users_data is not None:
            for user_id in users_data:
                user = User.objects.filter(id=user_id)
                if all(
                    [
                        user.exists(),
                        not Room.objects.filter(users__id=user_id).exists(),
                    ]
                ):
                    new_room.users.add(user.first())
        return new_room

    def get_users(self, obj):
        return [user.id for user in obj.users.all()]
