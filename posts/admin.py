from django.contrib import admin
from .models import Post, Like


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["id", "author", "content_preview", "created_at", "likes_count"]
    list_filter = ["created_at"]
    search_fields = ["author__username", "content"]

    def content_preview(self, obj):
        return obj.content[:50]

    def likes_count(self, obj):
        return obj.likes.count()


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ["user", "post", "created_at"]
