from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from config.throttling import FollowThrottle
from notify.tasks import create_follow_notification

from .models import Follow


class FollowUserView(APIView):
    permission_classes = [IsAuthenticated]
    # FollowThrottle was implemented in config/throttling.py but never
    # attached to any view — same unwired-throttle gap fixed for
    # Register/LoginThrottle earlier, left incomplete for this one.
    throttle_classes = [FollowThrottle]

    def post(self, request, user_id):
        # Previously compared request.user.id (a UUID object) directly to
        # user_id (a URL path param, which is a plain string unless the
        # URL conf uses a <uuid:...> converter) — UUID == str is always
        # False in Python, so the self-follow guard could silently never
        # trigger depending on the URL pattern. Casting both sides to str
        # makes this correct regardless of the URL conf.
        if str(request.user.id) == str(user_id):
            return Response({"error": "You cannot follow yourself"}, status=400)

        # Previously created the Follow without checking the target user
        # exists at all. A nonexistent user_id would either raise
        # IntegrityError (mapped to the misleading "Already following this
        # user" message) or, depending on FK/DB config, silently create a
        # dangling Follow row and fire a notification task for a
        # recipient_id that doesn't exist.
        if not User.objects.filter(id=user_id).exists():
            return Response({"error": "User not found"}, status=404)

        try:
            Follow.objects.create(follower=request.user, following_id=user_id)
        except IntegrityError:
            return Response({"error": "Already following this user"}, status=400)

        create_follow_notification.delay(str(request.user.id), str(user_id))

        return Response(
            {
                "status": "following",
                "follower_id": str(request.user.id),
                "following_id": str(user_id),
            },
            status=201,
        )


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

        if not User.objects.filter(id=user_id).exists():
            return Response({"error": "User not found"}, status=404)

        followers_count = Follow.objects.filter(following_id=user_id).count()
        following_count = Follow.objects.filter(follower_id=user_id).count()
        return Response(
            {"followers_count": followers_count, "following_count": following_count}
        )