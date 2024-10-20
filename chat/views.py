from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import CursorPagination
from .serializers import RoomSerializer, Room, MessageSerializer


class RoomMessagePagination(CursorPagination):
    page_size = 10
    ordering = "-created"


class RoomListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = RoomSerializer

    def get(self, request):
        rooms = Room.objects.all().order_by("-created")
        rooms_data = self.serializer_class(rooms, many=True).data
        return Response(rooms_data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"user": request.user}
        )
        if serializer.is_valid(raise_exception=True):
            room_data = serializer.save()
            response_data = self.serializer_class(room_data).data
            return Response(response_data, status=status.HTTP_201_CREATED)


class RoomHTMLView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = MessageSerializer
    pagination_class = RoomMessagePagination

    def get(self, request, room_id):
        room = (
            Room.objects.prefetch_related("messages").filter(id=room_id).first()
        )
        if room:
            messages = room.messages.order_by("-created")

            paginator = self.pagination_class()
            paginated_messages = paginator.paginate_queryset(
                messages, request, view=self
            )
            messages_list = self.serializer_class(paginated_messages, many=True).data

            context = {
                "chamber_id": room.id,
                "room_name": room.room_name,
                "messages": messages_list[::-1],
                "username": request.user.username,
                "previous_messages": paginator.get_next_link(),  # loads previous messages
            }

            if request.headers.get("Accept") == "application/json":
                return Response(
                    {
                        "results": messages_list,
                        "previous_messages": context["previous_messages"],
                    }
                )

            return render(request, "room.html", context)
        else:
            raise NotFound("Room with this id does not exist.")
