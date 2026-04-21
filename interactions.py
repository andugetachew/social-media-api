from django.urls import path
from .views import FollowToggleView, FollowersListView, FollowingListView, FollowStatsView

urlpatterns = [
    path('follow/<uuid:user_id>/', FollowToggleView.as_view(), name='follow'),
    path('followers/<uuid:user_id>/', FollowersListView.as_view(), name='followers'),
    path('following/<uuid:user_id>/', FollowingListView.as_view(), name='following'),
    path('stats/<uuid:user_id>/', FollowStatsView.as_view(), name='follow-stats'),
]