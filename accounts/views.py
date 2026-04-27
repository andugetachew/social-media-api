from django.shortcuts import render

# Create your views here.
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


User = get_user_model()


from django.core.mail import send_mail
from django.conf import settings
from .models import User
from django.utils import timezone


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
        user.bio = request.data.get("bio", user.bio)
        user.username = request.data.get("username", user.username)

        if "profile_picture" in request.FILES:
            user.profile_picture = request.FILES["profile_picture"]

        user.save()
        return Response(UserSerializer(user).data)


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
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "user": UserSerializer(user).data,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer
from .models import User


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password required"}, status=400)

        # Try to find user by email
        try:
            user = User.objects.get(email=email)

            # Check password
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "user": UserSerializer(user).data,
                    }
                )
        except User.DoesNotExist:
            pass

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

        # Update username
        if "username" in data:
            user.username = data["username"]

        # Update email
        if "email" in data:
            user.email = data["email"]

        # Update bio
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
