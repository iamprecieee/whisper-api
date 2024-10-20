from rest_framework.test import APITransactionTestCase
from .utils import (
    TestUser,
    add_user_to_room,
    remove_user_from_room,
    send_text_message,
    send_reply_text_message,
    send_image_message,
    send_audio_message,
    send_reply_image_message,
)
from channels.routing import URLRouter
from django.urls import path
from .consumers import RoomConsumer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
import json
from .models import Room
from user.models import JWTAccessToken
from django.urls import reverse
from user.utils import RefreshToken


User = get_user_model()


class RoomConsumerTestCase(APITransactionTestCase):
    async def asyncSetUp(self):
        user_instance = TestUser(
            email="admin@gmail.com",
            is_email_verified=True,
            is_2fa_enabled=True
        )
        self.user = await user_instance.create_user()
        self.token = await user_instance.create_token()
        
        user_instance2 = TestUser(
            email="admin2@gmail.com",
            username="admin",
            is_email_verified=True,
            is_2fa_enabled=True
        )
        self.user2 = await user_instance2.create_user()
        self.token2 = await user_instance2.create_token()
        
        self.room = await user_instance.create_room(room_name="test")
        self.application = URLRouter(
            [path("testws/room/<str:room_id>/", RoomConsumer.as_asgi())]
        )
        self.url = f"/testws/room/{self.room.id}/"
        
    async def test_chamber_consumer_connect_disconnect_success(self):
        await self.asyncSetUp()
        await add_user_to_room(self.room, self.user)
        
        # Test websocket connection
        communicator = WebsocketCommunicator(
            self.application,
            self.url,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        message = await communicator.receive_from()
        self.assertEqual(message, '{"type": "chat.active", "content": 1}')
        
        # Test adding new user to room
        await add_user_to_room(self.room, self.user2)
        
        message2 = await communicator.receive_from()
        self.assertEqual(message2, '{"type": "chat.notification", "content": "admin joined the chat."}')
        
        # Test sending number of active users
        communicator2 = WebsocketCommunicator(
            self.application,
            self.url,
            headers={"Authorization": f"Bearer {self.token2}"},
        )
        connected2, subprotocol = await communicator2.connect()
        self.assertTrue(connected2)
        
        message3 = await communicator.receive_from()
        self.assertEqual(message3, '{"type": "chat.active", "content": 2}')
        
        message4 = await communicator2.receive_from()
        self.assertEqual(message4, '{"type": "chat.active", "content": 2}')
        
        # Test sending text message
        await send_text_message(communicator2)
        await communicator.receive_from()
        message5 = await communicator2.receive_from()
        dict_message = json.loads(message5)
        self.assertEqual(dict_message["type"], "chat.message")
        self.assertEqual(dict_message["username"], "admin")
        
        # Test send text reply message
        await send_reply_text_message(communicator, previous_message_id=dict_message["id"])
        message6 = await communicator.receive_from()
        reply_dict_message = json.loads(message6)
        self.assertEqual(reply_dict_message["type"], "chat.reply")
        self.assertTrue(reply_dict_message["username"].startswith("user"))
        self.assertEqual(
            reply_dict_message["previous_message_content"], dict_message["text_content"]
        )
        self.assertEqual(reply_dict_message["previous_message_id"], dict_message["id"])

        # Test send image
        await send_image_message(communicator)
        message7 = await communicator.receive_from()
        image_dict_message = json.loads(message7)
        self.assertEqual(image_dict_message["type"], "chat.media")
        self.assertEqual(image_dict_message["filename"].endswith("png"), True)

        # # Test send audio
        # await send_audio_message(communicator)
        # message8 = await communicator.receive_from()
        # audio_dict_message = json.loads(message8)
        # self.assertEqual(audio_dict_message["type"], "chat.media")
        # self.assertEqual(audio_dict_message["filename"].endswith("wav"), True)

        # Test send image reply message
        await send_reply_image_message(
            communicator, previous_message_id=image_dict_message["id"]
        )
        message9 = await communicator.receive_from()
        image_reply_dict_message = json.loads(message9)
        self.assertEqual(image_reply_dict_message["type"], "chat.reply")
        self.assertEqual(image_reply_dict_message["username"], self.user.username)
        self.assertEqual(image_reply_dict_message["previous_message_content"], "IMAGE")
        self.assertEqual(
            image_reply_dict_message["previous_message_id"], image_dict_message["id"]
        )
        
        # Test removing user from room
        await remove_user_from_room(self.room, self.user2)
        message10 = await communicator.receive_from()
        self.assertEqual(message10, '{"type": "chat.notification", "content": "admin left the chat."}')
        
        # Test websocket disconnection
        await communicator.disconnect()
        user = await User.objects.filter(id=self.user.id).afirst()
        self.assertFalse(user.is_online)
         
    async def asyncTearDown(self):
        return super().tearDown()
        
        
class RoomListViewTestCase(APITransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="admin@gmail.com", password="Adm1!n123", is_email_verified=True, is_test_user=True
        )
        JWTAccessToken.objects.create(user=self.user)
        self.token = RefreshToken.for_user(self.user).access_token
        self.user.access_token.access_token = self.token
        self.user.access_token.save(update_fields=["access_token"])

        self.room = Room.objects.create(room_name="test", creator=self.user)

        self.url = reverse("chat:room-list")

    def test_retrieve_room_list_success(self):
        self.room.users.add(self.user)
        response = self.client.get(
            self.url, headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(type(response.data[0]), dict)
        self.assertEqual(response.status_code, 200)

    def test_create_room_success(self):
        response = self.client.post(
            self.url,
            headers={"Authorization": f"Bearer {self.token}"},
            data={"room_name": "test2", "user_ids": [self.user.id]},
        )
        self.assertIsNotNone(response.data["users"])

    def test_create_room_failure_existing_chambername(self):
        for i in range(2):
            response = self.client.post(
                self.url,
                headers={"Authorization": f"Bearer {self.token}"},
                data={"room_name": "test2", "user_ids": [self.user.id]},
            )
        self.assertEqual("Room with this room name already exists.", response.data)
        
    def tearDown(self):
        return super().tearDown()