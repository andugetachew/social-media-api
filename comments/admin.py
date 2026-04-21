from django.contrib import admin
from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["author", "post", "content_preview", "created_at"]

    def content_preview(self, obj):
        return obj.content[:50]
