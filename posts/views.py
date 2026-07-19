import logging

from django.db.models import QuerySet
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.throttling import LikeThrottle, PostCreateThrottle
from core.permissions import IsOwner
from interactions.models import Follow
from notify.tasks import create_like_notification

from .models import Post
from .selectors import PostSelector
from .serializers import CreatePostSerializer, PostSerializer
from .services import PostService

logger = logging.getLogger(__name__)


class FeedPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class FeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        page_size = min(page_size, 50)

        result = PostSelector.get_user_feed(
            user_id=str(request.user.id), page=page, page_size=page_size
        )

        serializer = PostSerializer(
            result["posts"], many=True, context={"request": request}
        )

        return Response(
            {
                "results": serializer.data,
                "count": result["total"],
                "page": result["page"],
                "page_size": result["page_size"],
                "total_pages": result["total_pages"],
                "next": (
                    f"/api/posts/feed/?page={result['page'] + 1}&page_size={page_size}"
                    if result["page"] < result["total_pages"]
                    else None
                ),
                "previous": (
                    f"/api/posts/feed/?page={result['page'] - 1}&page_size={page_size}"
                    if result["page"] > 1
                    else None
                ),
            }
        )


class PostListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        # PostCreateThrottle only makes sense for POST — GET (listing own
        # posts) shouldn't share that budget. PostCreateThrottle was
        # previously fully implemented in config/throttling.py but never
        # attached to any view — same unwired-throttle bug fixed earlier
        # for Register/LoginThrottle, left incomplete here.
        if self.request.method == "POST":
            self.throttle_classes = [PostCreateThrottle]
        else:
            self.throttle_classes = []
        return super().get_throttles()

    def get(self, request):
        """Get current user's posts."""
        posts = Post.objects.filter(author=request.user).order_by("-created_at")
        serializer = PostSerializer(posts, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        # Previously created Post directly via the ORM, bypassing
        # PostService.create_post entirely — which meant the fan-out
        # notification to followers (README: "On new post created") never
        # actually fired for real requests through this endpoint, and the
        # service's whitespace-only content check was skipped. Routed
        # through the service so both apply.
        serializer = CreatePostSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        content = serializer.validated_data.get("content", "")
        try:
            result = PostService.create_post(str(request.user.id), content)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        image = serializer.validated_data.get("image")
        if image:
            post = Post.objects.get(id=result["id"])
            post.image = image
            post.save(update_fields=["image"])

        post = Post.objects.get(id=result["id"])
        return Response(
            PostSerializer(post, context={"request": request}).data, status=201
        )


class PostDetailView(APIView):
    """
    Canonical single-post detail/update/delete view. PostDeleteView and
    PostUpdateView below duplicated this logic with slightly different
    status codes and response shapes — check urls.py for whether they're
    still routed anywhere; if not, prefer removing them in favor of this
    class alone. Left in place (now delegating here) rather than deleted
    outright, since I can't confirm from this file alone whether anything
    still points at them.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            result = PostSelector.get_post_with_like_status(
                post_id, str(request.user.id)
            )
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id, author=request.user)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)

        serializer = CreatePostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(PostSerializer(post, context={"request": request}).data)
        return Response(serializer.errors, status=400)

    def delete(self, request, post_id):
        try:
            PostService.delete_post(str(request.user.id), post_id)
            return Response(
                {"message": "Post deleted"}, status=status.HTTP_204_NO_CONTENT
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class PostDeleteView(APIView):
    """
    Duplicate of PostDetailView.delete() — kept only in case urls.py still
    routes to it separately. Now delegates to PostService.delete_post
    instead of its own raw ORM call, so it can't drift from
    PostDetailView's behavior again. Consider removing this class and
    pointing its URL at PostDetailView instead, if nothing else depends on
    its distinct 200-with-message response shape.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def delete(self, request, post_id):
        try:
            PostService.delete_post(str(request.user.id), post_id)
            return Response({"message": "Post deleted"}, status=200)
        except ValueError as e:
            return Response({"error": str(e)}, status=404)


class PostUpdateView(APIView):
    """
    Duplicate of PostDetailView.put() — same note as PostDeleteView above.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def put(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id, author=request.user)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)

        serializer = CreatePostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(PostSerializer(post, context={"request": request}).data)
        return Response(serializer.errors, status=400)


class LikeToggleView(APIView):
    """
    Previously defined twice in this file — Python silently kept only the
    second definition (this one, which sends the like notification). The
    first, dead definition has been removed rather than just left shadowed.
    """

    permission_classes = [IsAuthenticated]
    # LikeThrottle was implemented but never attached — same gap as
    # PostCreateThrottle above.
    throttle_classes = [LikeThrottle]

    def post(self, request, post_id):
        try:
            result = PostService.toggle_like(str(request.user.id), post_id)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        if result["liked"]:
            post = Post.objects.get(id=post_id)
            if str(post.author_id) != str(request.user.id):
                create_like_notification.delay(
                    str(post.author_id), str(request.user.id), str(post_id)
                )

        return Response(result, status=status.HTTP_200_OK)


class UserPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        
        try:
            posts = Post.objects.filter(author_id=user_id).order_by("-created_at")
            serializer = PostSerializer(posts, many=True, context={"request": request})
            return Response(serializer.data)
        except Exception:
            logger.exception("Failed to fetch posts for user_id=%s", user_id)
            return Response(
                {"error": "Unable to fetch posts"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )