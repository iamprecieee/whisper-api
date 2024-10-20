from nanoid import generate
from django.db.models import TextChoices
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
import json
from types import CoroutineType
from time import time
from random import randint
from base64 import b64decode
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.transaction import atomic


User = get_user_model()

def generate_room_name():
    return f"room-{generate(size=10)}"


class MessageFormat(TextChoices):
    TEXT = "TXT", "Text"
    IMAGE = "IMG", "Image"
    AUDIO = "AUD", "Audio"
    VIDEO = "VID", "Video"
    
    
class RoomDetail:
    def __init__(self, room_id):
        from .models import Room
        
        self.room_model = Room
        self.room_id = room_id
        
    async def retrieve_room_object(self):   
        return await self.room_model.objects.filter(id=self.room_id).afirst()

    async def retrieve_room_name(self):
        return await self.room_model.objects.filter(id=self.room_id).afirst().room_name
    
    async def get_active_users_count(self):
        room = await self.room_model.objects.prefetch_related("users").filter(id=self.room_id).afirst()
        return await room.users.filter(is_online=True).acount()


@sync_to_async
def confirm_authorization(headers):
    jwt_token = None
    if headers.get("Authorization"):
        jwt_token = headers["Authorization"].split(" ")[1]
    elif headers.get(b"authorization"):
        jwt_token = headers[b"authorization"].decode("utf-8").split(" ")[1]
    if jwt_token:
        payload = jwt.decode(jwt_token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        return User.objects.filter(id=user_id).first()
    

async def check_user_in_room(user_id, room_id):
    from .models import Room
    
    room = await Room.objects.prefetch_related("users").filter(id=room_id).afirst()
    return await room.users.filter(id=user_id).aexists()


async def set_user_status(user, status="online"):
    if status == "online":
        user.is_online = True
    elif status == "offline":
        user.is_online = False
    await user.asave()
    
class ConsumerMessage:
    def __init__(self, room):
        from .models import Message
        from .serializers import AsyncMessageSerializer
        
        self.message_model =  Message
        self.message_serializer = AsyncMessageSerializer
        self.room = room
        
    async def create_new_message(self, content, user):
        new_message = await self.message_model.objects.acreate(text_content=content, sender=user, room=self.room)
        new_message_data = self.message_serializer(new_message).data
        for key, value in new_message_data.items():
            if type(value) == CoroutineType:
                new_message_data[key] = await value
        return new_message_data

    async def get_replied_message(self, message_id):
        message = await self.message_model.objects.filter(id=message_id, room=self.room).afirst()
        message_data = self.message_serializer(message).data
        for key, value in message_data.items():
            if type(value) == CoroutineType:
                message_data[key] = await value
        return message_data

    async def create_new_reply(self, user, previous_sender, previous_content, previous_message_id, content=None, message_format="text"):
        new_reply = await self.message_model.objects.acreate(
            sender=user,
            previous_sender=previous_sender,
            previous_message_content=previous_content,
            previous_message_id=previous_message_id,
            room=self.room,
            is_reply=True,
        )
        if message_format == "text":
            new_reply.message_format = MessageFormat.TEXT
            new_reply.text_content = content
        elif message_format == "image":
            new_reply.message_format = MessageFormat.IMAGE
        elif message_format == "audio":
            new_reply.message_format = MessageFormat.AUDIO
        elif message_format == "video":
            new_reply.message_format = MessageFormat.VIDEO

        await new_reply.asave()
        return new_reply.id, new_reply.created
    
    async def create_new_media_message(self, media_format, user):
        new_message = await self.message_model.objects.acreate(sender=user, room=self.room)
        if media_format == "image":
            new_message.message_format = MessageFormat.IMAGE
        elif media_format == "audio":
            new_message.message_format = MessageFormat.AUDIO
        elif media_format == "video":
            new_message.message_format = MessageFormat.VIDEO

        await new_message.asave(update_fields=["message_format"])
        return new_message.id, new_message.created
    
    @sync_to_async
    def update_media_message(self, media_id, content, filename, media_format):
        media_data = b64decode(content)
        file_data = SimpleUploadedFile(
            name=filename,
            content=media_data,
        )
        media_message = self.message_model.objects.filter(id=media_id).first()
         
        with atomic():
            if media_format == "image":
                file_data.content_type = "image/png"
                media_message.message_type = MessageFormat.IMAGE
                media_message.image_content = file_data
            elif media_format == "audio":
                file_data.content_type = "audio/wav"
                media_message.message_type = MessageFormat.AUDIO
                media_message.audio_content = file_data
            elif media_format == "video":
                file_data.content_type = "video/mp4"
                media_message.message_type = MessageFormat.VIDEO
                media_message.video_content = file_data
                
            media_message.save()


async def generate_random_filename(media_format):
    timestamp = int(time() * 1000) 
    random_num = randint(0, 999999)
    if media_format == "image":
        extension = "png"
    elif media_format == "audio":
        extension = "wav"
    elif media_format == "video":
        extension = "mp4"
    return f"media_{timestamp}_{random_num}.{extension}"



class TestUser:
    def __init__(self, email, username=None, is_email_verified=False, is_2fa_enabled=False):
        from user.models import JWTAccessToken
        from .models import Room
        
        self.jwt_model = JWTAccessToken
        self.room_model = Room
        self.email = email
        self.username = username
        self.is_email_verified = is_email_verified
        self.is_2fa_enabled = is_2fa_enabled
        self.user = None
        self.access_token = None
        self.room = None
        
    @sync_to_async
    def create_user(self):
        user = User.objects.create_user(
            email=self.email,
            username=self.username,
            is_email_verified=self.is_email_verified,
            is_2fa_enabled=self.is_2fa_enabled,
        )
        self.user = user
        self.access_token = user.access_token.access_token
        return user

    @sync_to_async
    def create_token(self):
        new_refresh_token = RefreshToken.for_user(self.user)
        access_token = new_refresh_token.access_token
        self.user.access_token.access_token = access_token
        self.user.access_token.save(update_fields=["access_token"])
        self.access_token = access_token
        return access_token
    
    def create_room(self, room_name):
        room =  self.room_model.objects.acreate(room_name=room_name, creator=self.user)
        self.room = room
        return room
    
    
async def add_user_to_room(room, user):
    await room.users.aadd(user)
    

async def remove_user_from_room(room, user):
    await room.users.aremove(user)
    
    
def retrieve_user(user_id):
    return User.objects.filter(id=user_id).afirst()


async def send_text_message(communicator):
    message_data = {"message_type": "message", "message": "Hello. You."}
    await communicator.send_to(json.dumps(message_data))
    
    
async def send_reply_text_message(communicator, previous_message_id):
    message_data = {
        "message_type": "reply",
        "message": "Hello. You.",
        "previous_message_id": previous_message_id,
    }
    await communicator.send_to(json.dumps(message_data))


async def send_image_message(communicator):
    message_data = {"message_format": "image", "media_format": "image", "message_type": "media"}
    message_json = json.dumps(message_data).encode()
    delimiter = "<delimiter>".encode()

    image_file = settings.BASE_DIR/"test-image/test.png"
    with open(image_file, "rb") as file:
        image_data = file.read()

    combined_data = message_json + delimiter + image_data
    await communicator.send_to(bytes_data=combined_data)


async def send_audio_message(communicator):
    message_data = {"message_format": "audio", "media_format": "audio", "message_type": "media"}
    message_json = json.dumps(message_data).encode()
    delimiter = "<delimiter>".encode()

    audio_file = settings.BASE_DIR / "test-audio/test.wav"
    with open(audio_file, "rb") as file:
        audio_data = file.read()

    combined_data = message_json + delimiter + audio_data
    await communicator.send_to(bytes_data=combined_data)


async def send_reply_image_message(communicator, previous_message_id):
    message_data = {
        "message_type": "reply",
        "previous_message_id": previous_message_id,
        "media_format": "image",
    }
    message_json = json.dumps(message_data).encode()
    delimiter = "<delimiter>".encode()

    image_file = settings.BASE_DIR / "test-image/test.png"
    with open(image_file, "rb") as file:
        image_data = file.read()

    combined_data = message_json + delimiter + image_data
    await communicator.send_to(bytes_data=combined_data)