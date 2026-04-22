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

# from .views import delete_message
# from .views import upload_chat_file
# from django.urls import path
# from . import views

# urlpatterns = [
#     # Chat rooms & messages
#     path("rooms/", views.ChatRoomListView.as_view(), name="chat-rooms"),
#     path(
#         "messages/<uuid:user_id>/",
#         views.MessageListView.as_view(),
#         name="chat-messages",
#     ),
#     # Message actions
#     path("send/", views.send_message, name="send-message"),
#     path("poll/<uuid:user_id>/", views.get_messages, name="poll-messages"),
#     path("edit/<uuid:message_id>/", views.edit_message, name="edit-message"),
#     path("delete/<uuid:message_id>/", views.delete_message, name="delete-message"),
#     # Typing indicator
#     path("typing/", views.typing, name="typing"),
#     path("typing/<uuid:user_id>/", views.get_typing, name="get-typing"),
#     # File upload
#     path("upload/", views.upload_chat_file, name="upload-chat-file"),
# ]
