from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
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
            raise serializers.ValidationError({"password": "Passwords don't match"})
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
    """Validate login credentials."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
