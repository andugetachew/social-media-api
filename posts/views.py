from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Post
from .serializers import PostSerializer, CreatePostSerializer
from .services import PostService
from .selectors import PostSelector
from core.permissions import IsOwner
from rest_framework.pagination import PageNumberPagination
from django.db.models import QuerySet
from interactions.models import Follow

from notify.tasks import create_like_notification
from core.permissions import IsOwner


class PostDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def delete(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id, author=request.user)
            post.delete()
            return Response({"message": "Post deleted"}, status=200)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)


class FeedPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class FeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        # Limit page size to max 50
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

    def get(self, request):
        """Get current user's posts."""
        posts = Post.objects.filter(author=request.user).order_by("-created_at")
        serializer = PostSerializer(posts, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = CreatePostSerializer(data=request.data)
        if serializer.is_valid():
            post = Post.objects.create(
                author=request.user,
                content=serializer.validated_data.get("content", ""),
                image=serializer.validated_data.get("image"),
            )
            return Response(
                PostSerializer(post, context={"request": request}).data, status=201
            )
        return Response(serializer.errors, status=400)


class PostDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            result = PostSelector.get_post_with_like_status(
                post_id, str(request.user.id)
            )
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, post_id):  # ← add this
        try:
            post = Post.objects.get(id=post_id, author=request.user)
            serializer = CreatePostSerializer(post, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(PostSerializer(post, context={"request": request}).data)
            return Response(serializer.errors, status=400)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)

    def delete(self, request, post_id):
        try:
            PostService.delete_post(str(request.user.id), post_id)
            return Response(
                {"message": "Post deleted"}, status=status.HTTP_204_NO_CONTENT
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class LikeToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            result = PostService.toggle_like(str(request.user.id), post_id)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class UserPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            posts = Post.objects.filter(author_id=user_id).order_by("-created_at")
            serializer = PostSerializer(posts, many=True, context={"request": request})
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=404)


class PostUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def put(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id, author=request.user)
            serializer = CreatePostSerializer(post, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(PostSerializer(post, context={"request": request}).data)
            return Response(serializer.errors, status=400)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)


class LikeToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            result = PostService.toggle_like(str(request.user.id), post_id)
            # Send notification to post owner if liked
            if result["liked"]:
                post = Post.objects.get(id=post_id)
                if str(post.author_id) != str(request.user.id):
                    create_like_notification.delay(
                        str(post.author_id), str(request.user.id), str(post_id)
                    )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
