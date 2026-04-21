from rest_framework import serializers
from .models import Post, Like
from accounts.serializers import UserSerializer


class PostSerializer(serializers.ModelSerializer):
    """Serialize post with author details."""

    author = UserSerializer(read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    user_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "content",
            "created_at",
            "updated_at",
            "likes_count",
            "user_liked",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_user_liked(self, obj):
        """Check if current user liked this post."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False


class CreatePostSerializer(serializers.ModelSerializer):
    """Validate post creation."""

    class Meta:
        model = Post
        fields = ["content", "image"]

    def validate_content(self, value):
        if len(value) < 1:
            raise serializers.ValidationError("Content cannot be empty")
        if len(value) > 280:
            raise serializers.ValidationError("Content cannot exceed 280 characters")
        return value
