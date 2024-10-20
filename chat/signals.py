from django.dispatch import receiver
from django.db.models.signals import m2m_changed
from .models import Room
from .utils import retrieve_user
from channels.layers import get_channel_layer


channel_layer = get_channel_layer()

@receiver(m2m_changed, sender=Room.users.through)
async def notify_new_room_user(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for user_id in pk_set:
            user = await retrieve_user(user_id)
            await channel_layer.group_send(
                instance.id,
                {
                    "type": "chat.notification",
                    "content": f"{user.username} joined the chat."
                }
            )
            
    elif action == "post_remove":
        for user_id in pk_set:
            user = await retrieve_user(user_id)
            await channel_layer.group_send(
                instance.id,
                {
                    "type": "chat.notification",
                    "content": f"{user.username} left the chat."
                }
            )