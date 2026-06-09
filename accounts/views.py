from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from .services import UserService
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.db.models import Q
import uuid
User = get_user_model()
from notify.tasks import (
    send_verification_email,
    send_password_reset_email,
    send_welcome_email,
)
from django.contrib.auth import authenticate
from django.utils.crypto import get_random_string


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
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = User.objects.get(email_verification_token=token)
            user.email_verified = True
            user.save()
            return Response({"message": "Email verified successfully"})
        except User.DoesNotExist:
            return Response({"error": "Invalid token"}, status=400)


class ResendVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        send_mail(
            "Verify your email",
            f"Click the link to verify: http://127.0.0.1:8000/api/auth/verify/{user.email_verification_token}/",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return Response({"message": "Verification email sent"})

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

        # Blacklist all tokens
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
            if user.check_password(password):
                user.is_deleted = False
                user.is_active = True
                user.deleted_at = None
                user.save()
                return Response({"message": "Account reactivated"})
        except User.DoesNotExist:
            pass

        return Response({"error": "Invalid credentials"}, status=400)






class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Fix: use uuid4 instead of get_random_string
            verification_token = str(uuid.uuid4())
            user.email_verification_token = verification_token
            user.save()

            send_verification_email.delay(str(user.id), user.email, verification_token)

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
        return Response(serializer.errors, status=400)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        email = request.query_params.get("email")

        try:
            user = User.objects.get(email=email, email_verification_token=token)
            user.email_verified = True
            user.is_active = True
            user.save()

            # Send welcome email
            send_welcome_email.delay(str(user.id), user.email, user.username)

            return Response(
                {"message": "Email verified successfully. You can now login."}
            )
        except User.DoesNotExist:
            return Response({"error": "Invalid verification link"}, status=400)


class ResendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.email_verified:
            return Response({"error": "Email already verified"}, status=400)

        # Generate new token
        new_token = get_random_string(64)
        user.email_verification_token = new_token
        user.save()

        send_verification_email.delay(str(user.id), user.email, new_token)
        return Response({"message": "Verification email sent"})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
            reset_token = get_random_string(64)
            user.password_reset_token = reset_token
            user.save()
            send_password_reset_email.delay(str(user.id), user.email, reset_token)
            return Response({"message": "Password reset link sent to your email"})
        except User.DoesNotExist:
            return Response({"error": "Email not found"}, status=404)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        email = request.data.get("email")
        new_password = request.data.get("new_password")

        try:
            user = User.objects.get(email=email, password_reset_token=token)
            user.set_password(new_password)
            user.password_reset_token = ""
            user.save()
            return Response({"message": "Password reset successful"})
        except User.DoesNotExist:
            return Response({"error": "Invalid reset link"}, status=400)


class LoginView(APIView):
    permission_classes = [AllowAny]

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

        if user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                }
            )

        return Response({"error": "Invalid credentials"}, status=401)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
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
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("search", "")
        if query:
            users = User.objects.filter(username__icontains=query)[:10]
        else:
            users = User.objects.none()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


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

        user.save()
        return Response(UserSerializer(user).data)


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
