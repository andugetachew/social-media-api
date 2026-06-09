from django.urls import path
from .views import upload_chat_file
from .views import (
    ChatRoomListView,
    MessageListView,
    send_message,
    get_messages,
    typing,
    get_typing,
    edit_message,
    delete_message,
)

urlpatterns = [
    path("rooms/", ChatRoomListView.as_view(), name="chat-rooms"),
    path("messages/<uuid:user_id>/", MessageListView.as_view(), name="chat-messages"),
    path("send/", send_message, name="send-message"),
    path("poll/<uuid:user_id>/", get_messages, name="poll-messages"),
    path("typing/", typing, name="typing"),
    path("typing/<uuid:user_id>/", get_typing, name="get-typing"),
    path("edit/<uuid:message_id>/", edit_message, name="edit-message"),
    path("delete/<uuid:message_id>/", delete_message, name="delete-message"),
    path("upload/", upload_chat_file, name="upload-chat-file"),
]

