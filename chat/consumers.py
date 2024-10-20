from channels.generic.websocket import AsyncWebsocketConsumer
from .utils import (
    RoomDetail,
    confirm_authorization,
    check_user_in_room,
    set_user_status,
    ConsumerMessage,
    generate_random_filename,
)
import json
from django.utils.dateformat import format
from base64 import b64encode


class RoomConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room = None
        self.room_group_name = None
        self.user = None
        self.room_instance = None
        self.consumer_message_instance = None
        
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_instance = RoomDetail(self.room_id)
        self.room = await self.room_instance.retrieve_room_object()
        self.room_group_name = self.room_id
        
        headers = dict(self.scope["headers"])
        self.user = await confirm_authorization(headers)
        
        user_in_room = await check_user_in_room(self.user.id, self.room_id)
        if not user_in_room:
            await self.close(code=4001)
        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        await set_user_status(self.user)
        active_count = await self.room_instance.get_active_users_count()
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat.active", "content": active_count}
        )
        
    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await set_user_status(self.user, status="offline")
        
        active_count = await self.room_instance.get_active_users_count()
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat.active", "content": active_count}
        )
        
    async def receive(self, text_data=None, bytes_data=None):
        self.consumer_message_instance = ConsumerMessage(self.room)
        
        if text_data:
            text_data_json = json.loads(text_data)
            message = text_data_json.get("message")
            message_type = text_data_json.get("message_type")
            
            if message_type == "message":
                if message:
                    new_message_data = await self.consumer_message_instance.create_new_message(message, self.user)
                    
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "chat.message",
                            "id": new_message_data["id"],
                            "text_content": message,
                            "message_format": "text",
                            "username": self.user.username,
                            "created": new_message_data["date"],
                            "time": new_message_data["time"],
                        },
                    )
            elif message_type == "reply":
                previous_message_id = text_data_json.get("previous_message_id")
                if message:
                    replied_message = await self.consumer_message_instance.get_replied_message(previous_message_id)
                    if replied_message["message_format"] == "IMG":
                        previous_message_content = "IMAGE"
                    elif replied_message["message_format"] == "AUD":
                        previous_message_content = "AUDIO"
                    elif replied_message["message_format"] == "VID":
                        previous_message_content = "VIDEO"
                    else:
                        previous_message_content = replied_message["text_content"]

                    reply_id, created = await self.consumer_message_instance.create_new_reply(
                        self.user,
                        replied_message["sender"],
                        previous_message_content,
                        previous_message_id,
                        message,
                    )
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "chat.reply",
                            "is_reply": True,
                            "reply_format": "text",
                            "id": reply_id,
                            "text_content": message,
                            "message_format": "text",
                            "previous_sender_username": replied_message["username"],
                            "previous_message_content": previous_message_content,
                            "previous_message_id": previous_message_id,
                            "username": self.user.username,
                            "created": format(created, "M. d, Y"),
                            "time": format(created, "P"),
                        },
                    )
            elif message_type == "typing":
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat.typing",
                        "username": self.user.username,
                        "content": (
                            f"{self.user} is typing..." if message == "typing" else None
                        ),
                    },
                )
        elif bytes_data:
            delimiter = b"<delimiter>"
            
            if delimiter in bytes_data:
                json_data, media_data =  bytes_data.split(delimiter, 1)
                if media_data == b"":
                    await self.channel_layer.group_send(
                        self.room_group_name, {"type": "chat.error", "content": "No file detected or invalid file data."}
                    )
                
                metadata = json.loads(json_data.decode("utf-8"))
                message_type = metadata.get("message_type")
                message_format = metadata.get("message_format")
                media_format = metadata.get("media_format")
                
                message = b64encode(media_data).decode("utf-8")
                filename = await generate_random_filename(media_format)
                
                if message_type == "media":
                    new_media_message_id, created = await self.consumer_message_instance.create_new_media_message(media_format, self.user)
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "chat.media",
                            "id": new_media_message_id,
                            "content": message,
                            "media_format": media_format,
                            "message_format": "media",
                            "filename": filename,
                            "username": self.user.username,
                            "created": format(created, "M. d, Y"),
                            "time": format(created, "P"),
                        },
                    )
                    
                    await self.consumer_message_instance.update_media_message(new_media_message_id, message, filename, media_format)
                else:
                    previous_message_content = None
                    previous_message_id = metadata.get("previous_message_id")
                    replied_message = await self.consumer_message_instance.get_replied_message(previous_message_id)
                    if replied_message["message_format"] == "IMG":
                        previous_message_content = "IMAGE"
                    elif replied_message["message_format"] == "AUD":
                        previous_message_content = "AUDIO"
                    elif replied_message["message_format"] == "VID":
                        previous_message_content = "VIDEO"
                    else:
                        previous_message_content = replied_message["text_content"]

                    new_media_reply_id, created = await self.consumer_message_instance.create_new_reply(
                        self.user,
                        replied_message["sender"],
                        previous_message_content,
                        previous_message_id,
                        message_format=message_format,
                    )
                    
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "chat.reply",
                            "is_reply": True,
                            "reply_format": "media",
                            "message_format": "media",
                            "id": new_media_reply_id,
                            "content": message,
                            "media_format": media_format,
                            "filename": filename,
                            "previous_sender_username": replied_message["username"],
                            "previous_message_content": previous_message_content,
                            "previous_message_id": previous_message_id,
                            "time": format(created, "P"),
                            "created": format(created, "M. d, Y"),
                            "username": self.user.username,
                        },
                    )
                    await self.consumer_message_instance.update_media_message(new_media_reply_id, message, filename, media_format)

    async def chat_active(self, event):
        text_data = json.dumps(event)
        await self.send(text_data)
        
    async def chat_notification(self, event):
        text_data = json.dumps(event)
        await self.send(text_data)
        
    async def chat_message(self, event):
        text_data = json.dumps(event)
        await self.send(text_data)
        
    async def chat_reply(self, event):
        text_data = json.dumps(event)
        await self.send(text_data)
        
    async def chat_media(self, event):
        text_data = json.dumps(event)
        await self.send(text_data)
        
    async def chat_typing(self, event):
        text_data = json.dumps(event)
        await self.send(text_data)
        
    async def chat_error(self, event):
        text_data = json.dumps(event)
        await self.send(text_data)    