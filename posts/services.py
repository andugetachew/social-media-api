from notify.tasks import fan_out_notification_to_followers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Post, Like
from interactions.models import Follow
from typing import Dict

User = get_user_model()


class PostService:
    @staticmethod
    def create_post(author_id: str, content: str) -> Dict:
        """Create a new post with background notifications."""
        if not content or len(content) > 280:
            raise ValueError("Content must be 1-280 characters")

        with transaction.atomic():
            post = Post.objects.create(author_id=author_id, content=content)

            # Get follower count
            follower_count = Follow.objects.filter(following_id=author_id).count()

            # NEW: Fan out notifications in background (does NOT block response)
            if follower_count > 0:
                author = User.objects.get(id=author_id)
                fan_out_notification_to_followers.delay(
                    author_id,
                    str(post.id),
                    f"{author.username} posted new content",
                    follower_count,
                )

            return {
                "id": str(post.id),
                "content": post.content,
                "created_at": post.created_at,
                "author_id": str(post.author_id),
                "notifications_queued": follower_count,  # Shows user we queued them
            }

    @staticmethod
    def delete_post(user_id: str, post_id: str) -> bool:
        """Delete a post only if user is the author."""
        try:
            post = Post.objects.get(id=post_id, author_id=user_id)
            post.delete()
            return True
        except Post.DoesNotExist:
            raise ValueError("Post not found or you don't have permission")

    @staticmethod
    def toggle_like(user_id: str, post_id: str) -> Dict:
        # Check post exists first
        try:
            Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            raise ValueError("Post not found")

        like, created = Like.objects.get_or_create(user_id=user_id, post_id=post_id)
        if not created:
            like.delete()
            return {
                "liked": False,
                "likes_count": Like.objects.filter(post_id=post_id).count(),
            }
        return {
            "liked": True,
            "likes_count": Like.objects.filter(post_id=post_id).count(),
        }
