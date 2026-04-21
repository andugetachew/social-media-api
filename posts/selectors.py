from django.db.models import QuerySet
from .models import Post, Like
from interactions.models import Follow
from typing import Dict
from django.db.models import Q


class PostSelector:
    @staticmethod
    def get_user_feed(user_id: str, page: int = 1, page_size: int = 10):
        """Get posts from users I follow + my own posts"""

        # Get IDs of users being followed
        following_ids = Follow.objects.filter(follower_id=user_id).values_list(
            "following_id", flat=True
        )

        # Convert to list for Q lookup
        following_list = list(following_ids)

        # Add current user to see their own posts
        following_list.append(user_id)

        # Query: posts from followed users OR current user
        posts = (
            Post.objects.filter(author_id__in=following_list)
            .select_related("author")
            .prefetch_related("likes", "comments")
            .order_by("-created_at")
        )

        # Manual pagination
        start = (page - 1) * page_size
        end = start + page_size
        total = posts.count()

        return {
            "posts": posts[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    @staticmethod
    def get_post_with_like_status(post_id: str, current_user_id: str) -> Dict:
        """Get single post with boolean if current user liked it."""
        try:
            post = Post.objects.select_related("author").get(id=post_id)
            user_liked = Like.objects.filter(
                post_id=post_id, user_id=current_user_id
            ).exists()

            return {
                "id": str(post.id),
                "content": post.content,
                "created_at": post.created_at,
                "author": {
                    "id": str(post.author.id),
                    "username": post.author.username,
                    "avatar_url": post.author.avatar_url,
                },
                "likes_count": post.likes.count(),
                "user_liked": user_liked,
            }
        except Post.DoesNotExist:
            raise ValueError("Post not found")
