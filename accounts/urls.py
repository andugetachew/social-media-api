from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    MeView,
    LogoutView,
    UserDetailView,
    UserSearchView,
    UpdateOnlineStatusView,
    UserStatusView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("users/<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("users/", UserSearchView.as_view(), name="user-search"),
    path("online/", UpdateOnlineStatusView.as_view(), name="update-online"),
    path("status/<uuid:user_id>/", UserStatusView.as_view(), name="user-status"),
]
