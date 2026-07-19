from django.urls import path

from .views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationListView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications"),
    path(
        "<uuid:notification_id>/read/",
        MarkNotificationReadView.as_view(),
        name="mark-read",
    ),
 
    path(
        "mark-all-read/",
        MarkAllNotificationsReadView.as_view(),
        name="mark-all-read",
    ),
]