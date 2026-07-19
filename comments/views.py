from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsCommentOwner
from posts.models import Post

from .models import Comment
from .serializers import CommentSerializer, CreateCommentSerializer


class CommentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        # Previously fetched by id alone, with no is_active check. The
        # `moderation` app has no models of its own — is_active/is_flagged
        # live directly on Post and were never enforced anywhere. A
        # deactivated/flagged post's comments were still fully readable.
        try:
            post = Post.objects.get(id=post_id, is_active=True)
            comments = post.comments.select_related("author").all()
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)

    def post(self, request, post_id):
        # Same fix here: previously allowed new comments on a
        # deactivated/flagged post.
        try:
            post = Post.objects.get(id=post_id, is_active=True)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)

        serializer = CreateCommentSerializer(data=request.data)
        if serializer.is_valid():
            comment = Comment.objects.create(
                author=request.user,
                post=post,
                content=serializer.validated_data["content"],
            )
            return Response(CommentSerializer(comment).data, status=201)
        return Response(serializer.errors, status=400)


class CommentDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsCommentOwner]

    def delete(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id)
            self.check_object_permissions(request, comment)
            comment.delete()
            return Response({"message": "Comment deleted"}, status=200)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)