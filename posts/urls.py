from django.urls import path
from .views import (
    FeedView,
    PostListCreateView,
    PostDetailView,
    LikeToggleView,
    UserPostsView,
    PostUpdateView,
)

urlpatterns = [
    path("feed/", FeedView.as_view(), name="feed"),
    path("", PostListCreateView.as_view(), name="posts"),
    path("<uuid:post_id>/", PostDetailView.as_view(), name="post-detail"),
    path("<uuid:post_id>/like/", LikeToggleView.as_view(), name="like"),
    path("user/<uuid:user_id>/", UserPostsView.as_view(), name="user-posts"),
    path("<uuid:post_id>/update/", PostUpdateView.as_view(), name="post-update"),
]
