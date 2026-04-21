from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from posts.models import Post
from .models import Comment
from .serializers import CommentSerializer, CreateCommentSerializer

from core.permissions import IsCommentOwner


class CommentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            comments = post.comments.select_related("author").all()
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            serializer = CreateCommentSerializer(data=request.data)
            if serializer.is_valid():
                comment = Comment.objects.create(
                    author=request.user,
                    post=post,
                    content=serializer.validated_data["content"],
                )
                return Response(CommentSerializer(comment).data, status=201)
            return Response(serializer.errors, status=400)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)


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
