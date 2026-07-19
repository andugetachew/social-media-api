from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user).order_by(
            "-created_at"
        )[:50]
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id, recipient=request.user
            )
            notification.is_read = True
            notification.save()
            return Response({"status": "marked as read"})
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=404)


class MarkAllNotificationsReadView(APIView):
    """
    Was documented in the README's endpoint table
    (POST /api/notifications/mark-all-read/) but had no corresponding view
    in this file — added here. Scoped to request.user via recipient=,
    same as the other views in this file, so it can't touch another
    user's notifications.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({"status": "all marked as read", "count": updated_count})