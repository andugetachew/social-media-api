from celery import shared_task
from django.contrib.auth import get_user_model
from .models import Notification
from interactions.models import Follow

User = get_user_model()


@shared_task
def send_single_notification(recipient_id, sender_id, post_id, message):
    try:
        Notification.objects.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            notification_type="like",
            message=message,
        )
    except Exception as e:
        print(f"Failed: {e}")


@shared_task
def fan_out_notification_to_followers(author_id, post_id, message, follower_count):
    followers = Follow.objects.filter(following_id=author_id).values_list(
        "follower_id", flat=True
    )

    for follower_id in followers:
        send_single_notification.delay(follower_id, author_id, post_id, message)

    return {"notifications_sent": len(followers), "status": "processing"}
