from django.contrib.auth import get_user_model
from django.db.models import (
    Model, 
    CharField,
    ManyToManyField,
    ForeignKey,
    CASCADE,
    DateTimeField,
    TextField,
    ImageField, 
    FileField,
    BooleanField
)
from nanoid import generate
from .utils import generate_room_name, MessageFormat

User = get_user_model()


class Room(Model):
    id = CharField(max_length=21, primary_key=True, editable=False, unique=True, default=generate)
    room_name = CharField(max_length=200, blank=False, unique=True, db_index=True)
    users = ManyToManyField(User)
    creator = ForeignKey(User, related_name="created_rooms", on_delete=CASCADE)
    created = DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.room_name

    def save(self, *args, **kwargs) -> None:
        if not self.room_name:
            self.room_name = generate_room_name()
        return super().save(*args, **kwargs)


class Message(Model):
    id = CharField(max_length=21, primary_key=True, editable=False, unique=True, default=generate)
    message_format = CharField(
        max_length=3, choices=MessageFormat.choices, default=MessageFormat.TEXT, db_index=True
    )
    text_content = TextField(blank=True)
    image_content = ImageField(upload_to="images/", blank=True)
    audio_content = FileField(upload_to="audios/", blank=True)
    video_content = FileField(upload_to="videos/", blank=True)
    is_reply = BooleanField(default=False, db_index=True)
    previous_message_content = TextField(blank=True, null=True)
    previous_message_id = CharField(max_length=21, blank=True, null=True, db_index=True)
    previous_sender = CharField(max_length=50, blank=True, null=True)
    sender = ForeignKey(User, related_name="sent_messages", on_delete=CASCADE)
    room = ForeignKey(Room, related_name="messages", on_delete=CASCADE)
    created = DateTimeField(auto_now_add=True, db_index=True)
    updated = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.get_message_type_display()} message from {self.sender}"
