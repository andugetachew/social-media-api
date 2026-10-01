# from rest_framework import serializers
# from django.contrib.auth.password_validation import validate_password
# from .models import User


# class UserSerializer(serializers.ModelSerializer):
#     """Serialize user model for API responses."""

#     class Meta:
#         model = User
#         fields = [
#             "id",
#             "email",
#             "full_name",
#             "username",
#             "bio",
#             "avatar_url",
#             "created_at",
#         ]
#         read_only_fields = ["id", "created_at"]


# class RegisterSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, required=True)
#     password2 = serializers.CharField(write_only=True, required=True)

#     class Meta:
#         model = User
#         fields = ["email", "username", "full_name", "password", "password2"]

#     def validate(self, attrs):
#         if attrs["password"] != attrs["password2"]:
#             raise serializers.ValidationError({"password": "Passwords don't match"})
#         return attrs

#     def create(self, validated_data):
#         validated_data.pop("password2")
#         user = User.objects.create_user(
#             email=validated_data["email"],
#             username=validated_data["username"],
#             password=validated_data["password"],
#             full_name=validated_data.get("full_name", ""),
#         )
#         return user


# class LoginSerializer(serializers.Serializer):
#     """Validate login credentials."""

#     email = serializers.EmailField(required=True)
#     password = serializers.CharField(required=True, write_only=True)

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serialize user model for API responses."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "username",
            "bio",
            "avatar_url",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["email", "username", "full_name", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords don't match"})

        # Temporary (unsaved) user so similarity checks against
        # username/email/full_name work. DRF turns Django's ValidationError
        # into a normal 400 response.
        temp_user = User(
            email=attrs.get("email"),
            username=attrs.get("username"),
            full_name=attrs.get("full_name", ""),
        )
        validate_password(attrs["password"], temp_user)
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            full_name=validated_data.get("full_name", ""),
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Validate login credentials. `email` accepts an email OR a username."""

    email = serializers.CharField(
        required=True,
        help_text="Email address or username",
    )
    password = serializers.CharField(required=True, write_only=True)


# --------------------------------------------------------------------------
# Request serializers (used for API docs; views still read request.data)
# --------------------------------------------------------------------------


class ReactivateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)


class UpdatePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class OnlineStatusSerializer(serializers.Serializer):
    is_online = serializers.BooleanField(default=True)


class ProfilePhotoSerializer(serializers.Serializer):
    profile_picture = serializers.ImageField()


class UpdateProfileSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    bio = serializers.CharField(required=False, allow_blank=True)
    profile_picture = serializers.ImageField(required=False)


# --------------------------------------------------------------------------
# Response serializers (documentation only)
# --------------------------------------------------------------------------


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


class RegisterResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    access = serializers.CharField()
    refresh = serializers.CharField()
    message = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class UserStatusResponseSerializer(serializers.Serializer):
    is_online = serializers.BooleanField()
    last_seen = serializers.DateTimeField(allow_null=True)


class ProfilePhotoResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    url = serializers.CharField()


class StatusUpdatedSerializer(serializers.Serializer):
    status = serializers.CharField()
