from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    DeleteAccountView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    ReactivateAccountView,
    RegisterView,
    ResendVerificationEmailView,
    UpdateOnlineStatusView,
    UpdatePasswordView,
    UpdateProfilePhotoView,
    UpdateProfileView,
    UserDetailView,
    UserSearchView,
    UserStatusView,
    VerifyEmailView,
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
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("update-profile/", UpdateProfileView.as_view(), name="update-profile"),
    path("update-password/", UpdatePasswordView.as_view(), name="update-password"),
    path("update-photo/", UpdateProfilePhotoView.as_view(), name="update-photo"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete-account"),
    path("reactivate/", ReactivateAccountView.as_view(), name="reactivate-account"),

    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path(
        "resend-verification/",
        ResendVerificationEmailView.as_view(),
        name="resend-verification",
    ),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path(
        "password-reset-confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]