import uuid
from typing import Dict

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from interactions.models import Follow
from notify.tasks import fan_out_notification_to_followers
from .models import Like, Post

User = get_user_model()


class PostService:
    @staticmethod
    def create_post(author_id: str, content: str) -> Dict:
        """Create a new post with background notifications."""
        if not content or not content.strip() or len(content) > 280:
            raise ValueError("Content must be 1-280 characters")

        with transaction.atomic():
            post = Post.objects.create(author_id=author_id, content=content)

            follower_count = Follow.objects.filter(following_id=author_id).count()

            if follower_count > 0:
                author = User.objects.get(id=author_id)

                # transaction.on_commit defers the .delay() call until this
                # transaction actually commits. Previously .delay() fired
                # immediately inside the atomic block — with Redis as the
                # broker, a worker can pick up the task and query for this
                # post before the transaction commits and the row becomes
                # visible, since .delay() doesn't wait for commit.
                post_id = str(post.id)
                transaction.on_commit(
                    lambda: fan_out_notification_to_followers.delay(
                        author_id,
                        post_id,
                        f"{author.username} posted new content",
                        follower_count,
                    )
                )

            return {
                "id": str(post.id),
                "content": post.content,
                "created_at": post.created_at,
                "author_id": str(post.author_id),
                "notifications_queued": follower_count,
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

    
        try:
            like, created = Like.objects.get_or_create(user_id=user_id, post_id=post_id)
        except IntegrityError:
            like, created = Like.objects.get(user_id=user_id, post_id=post_id), False

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