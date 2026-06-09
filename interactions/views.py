from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import IntegrityError
from accounts.models import User
from .models import Follow
from notify.tasks import create_follow_notification


class FollowUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if request.user.id == user_id:  # UUID to UUID comparison
            return Response({"error": "You cannot follow yourself"}, status=400)
        try:
            follow = Follow.objects.create(follower=request.user, following_id=user_id)
            create_follow_notification.delay(str(request.user.id), str(user_id))
            return Response(
                {
                    "status": "following",
                    "follower_id": str(request.user.id),
                    "following_id": str(user_id),
                },
                status=201,
            )
        except IntegrityError:
            return Response({"error": "Already following this user"}, status=400)


class UnfollowUserView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        """Unfollow a user."""
        deleted, _ = Follow.objects.filter(
            follower=request.user, following_id=user_id
        ).delete()

        if deleted:
            return Response({"status": "unfollowed"}, status=200)
        return Response({"error": "Not following this user"}, status=400)


class CheckFollowView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        is_following = Follow.objects.filter(
            follower=request.user, following_id=user_id
        ).exists()
        return Response({"is_following": is_following})


class FollowersListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            followers = user.followers.select_related("follower")
            users = [follow.follower for follow in followers]
            from accounts.serializers import UserSerializer

            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


class FollowingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            following = user.following.select_related("following")
            users = [follow.following for follow in following]
            from accounts.serializers import UserSerializer

            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


class FollowStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            followers_count = Follow.objects.filter(following_id=user_id).count()
            following_count = Follow.objects.filter(follower_id=user_id).count()
            return Response(
                {"followers_count": followers_count, "following_count": following_count}
            )
        except Exception:
            return Response({"followers_count": 0, "following_count": 0})
