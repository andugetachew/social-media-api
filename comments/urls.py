from django.urls import path
from .views import CommentListCreateView, CommentDeleteView

urlpatterns = [
    path("post/<uuid:post_id>/", CommentListCreateView.as_view(), name="comments"),
    path("<uuid:comment_id>/", CommentDeleteView.as_view(), name="comment-delete"),
]
