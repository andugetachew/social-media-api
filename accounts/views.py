import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.crypto import get_random_string

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from notify.tasks import (
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)
from config.throttling import (
    BurstRateThrottle,
    LoginThrottle,
    RegisterThrottle,
    SustainedRateThrottle,
)
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

User = get_user_model()


class UpdateOnlineStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.is_online = request.data.get("is_online", True)
        user.last_seen = timezone.now()
        user.save()
        return Response({"status": "updated"})


class UserStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            other_user = User.objects.get(id=user_id)
            return Response(
                {"is_online": other_user.is_online, "last_seen": other_user.last_seen}
            )
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


class EmailVerificationView(APIView):
    """
    Legacy token-in-path verification link (kept for backward compatibility
    with any existing emailed links). Prefer VerifyEmailView going forward.
    """

    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = User.objects.get(email_verification_token=token)
        except User.DoesNotExist:
            return Response({"error": "Invalid token"}, status=400)

        user.email_verified = True
        user.is_active = True
        user.save()
        return Response({"message": "Email verified successfully"})




class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        data = request.data

        if "username" in data:
            user.username = data["username"]

        if "email" in data:
            user.email = data["email"]

        if "bio" in data:
            user.bio = data["bio"]

        if "profile_picture" in request.FILES:
            user.profile_picture = request.FILES["profile_picture"]

        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.is_active = False
        user.save()

        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

        OutstandingToken.objects.filter(user=user).delete()

        return Response({"message": "Account deleted successfully"})


class ReactivateAccountView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        try:
            user = User.objects.get(email=email, is_deleted=True)
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=400)

        if user.check_password(password):
            user.is_deleted = False
            user.is_active = True
            user.deleted_at = None
            user.save()
            return Response({"message": "Account reactivated"})

        return Response({"error": "Invalid credentials"}, status=400)


class RegisterView(APIView):
    permission_classes = [AllowAny]
   
    throttle_classes = [RegisterThrottle, BurstRateThrottle, SustainedRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        user = serializer.save()


        user.is_active = False
        user.email_verification_token = str(uuid.uuid4())
        user.save()

        send_verification_email.delay(
            str(user.id), user.email, user.email_verification_token
        )

        # Token is still issued so the client can, e.g., poll verification
        # status — but protected views must check is_active/email_verified,
        # not just token validity, since the account isn't active yet.
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "message": "Please verify your email",
            },
            status=201,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        email = request.query_params.get("email")

        try:
            user = User.objects.get(email=email, email_verification_token=token)
        except User.DoesNotExist:
            return Response({"error": "Invalid verification link"}, status=400)

        user.email_verified = True
        user.is_active = True
        user.save()

        send_welcome_email.delay(str(user.id), user.email, user.username)

        return Response({"message": "Email verified successfully. You can now login."})


class ResendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.email_verified:
            return Response({"error": "Email already verified"}, status=400)

        new_token = str(uuid.uuid4())
        user.email_verification_token = new_token
        user.save()

        send_verification_email.delay(str(user.id), user.email, new_token)
        return Response({"message": "Verification email sent"})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

     
        generic_response = Response(
            {"message": "If that email is registered, a reset link has been sent."}
        )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return generic_response

        reset_token = get_random_string(64)
        user.password_reset_token = reset_token
        user.save()
        send_password_reset_email.delay(str(user.id), user.email, reset_token)

        return generic_response


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        email = request.data.get("email")
        new_password = request.data.get("new_password")

        try:
            user = User.objects.get(email=email, password_reset_token=token)
        except User.DoesNotExist:
            return Response({"error": "Invalid reset link"}, status=400)

        # Previously missing: reset path let a caller set an arbitrarily
        # weak password, unlike UpdatePasswordView which validates.
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"error": e.messages}, status=400)

        user.set_password(new_password)
        user.password_reset_token = ""
        user.save()
        return Response({"message": "Password reset successful"})


class LoginView(APIView):
    permission_classes = [AllowAny]
    # Same gap as RegisterView, plus the same replace-not-extend fix.
    throttle_classes = [LoginThrottle, BurstRateThrottle, SustainedRateThrottle]

    def post(self, request):
        email_or_username = request.data.get("email")
        password = request.data.get("password")

        if not email_or_username or not password:
            return Response(
                {"error": "Email/Username and password required"}, status=400
            )

        try:
            if "@" in email_or_username:
                user = User.objects.get(email=email_or_username)
            else:
                user = User.objects.get(username=email_or_username)
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=401)

        if not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=401)

        
        if not user.is_active:
            if getattr(user, "is_deleted", False):
                return Response(
                    {"error": "Account is deactivated. Please reactivate it first."},
                    status=403,
                )
            return Response(
                {"error": "Please verify your email before logging in."}, status=403
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
       
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Logged out successfully"}, status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        return Response(UserSerializer(user).data)


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("search", "")
        if query:
            users = User.objects.filter(username__icontains=query)[:10]
        else:
            users = User.objects.none()
        return Response(UserSerializer(users, many=True).data)


class UpdatePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not user.check_password(old_password):
            return Response({"error": "Wrong password"}, status=400)

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"error": e.messages}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Password updated successfully"})


class UpdateProfilePhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if "profile_picture" not in request.FILES:
            return Response({"error": "No image provided"}, status=400)

        user = request.user
        user.profile_picture = request.FILES["profile_picture"]
        user.save()
        return Response(
            {"message": "Profile photo updated", "url": user.profile_picture.url}
        )