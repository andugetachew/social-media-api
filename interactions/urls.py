from django.urls import path
from .views import (
    FollowUserView,
    UnfollowUserView,
    CheckFollowView,
    FollowersListView,
    FollowingListView,
    FollowStatsView,
)

urlpatterns = [
    path("follow/<uuid:user_id>/", FollowUserView.as_view(), name="follow"),
    path("unfollow/<uuid:user_id>/", UnfollowUserView.as_view(), name="unfollow"),
    path("check/<uuid:user_id>/", CheckFollowView.as_view(), name="check-follow"),
    path("followers/<uuid:user_id>/", FollowersListView.as_view(), name="followers"),
    path("following/<uuid:user_id>/", FollowingListView.as_view(), name="following"),
    path("stats/<uuid:user_id>/", FollowStatsView.as_view(), name="follow-stats"),
]
