import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from interactions.models import Follow
from .models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_single_notification(self, recipient_id, sender_id, post_id, message):
    """
    Creates a single notification for a follower as part of a fan-out.
    notification_type is "new_post" — this task is only ever invoked from
    fan_out_notification_to_followers (post-created fan-out), never from a
    like event. Previously hardcoded to "like", mislabeling every fan-out
    notification.
    """
    try:
        Notification.objects.create(
            recipient_id=recipient_id,
            sender_id=sender_id,
            notification_type="new_post",
            message=message,
        )
    except Exception as exc:
        logger.exception(
            "Failed to create fan-out notification: recipient=%s sender=%s post=%s",
            recipient_id, sender_id, post_id,
        )
        raise self.retry(exc=exc)


@shared_task
def fan_out_notification_to_followers(author_id, post_id, message, follower_count):
    followers = list(
        Follow.objects.filter(following_id=author_id).values_list(
            "follower_id", flat=True
        )
    )

    # follower_count is the caller's expected count (e.g. captured at the
    # moment the post was created); log a mismatch instead of silently
    # discarding it — a large gap can indicate a race between post creation
    # and this task running (mass unfollow/follow in between).
    actual_count = len(followers)
    if follower_count is not None and actual_count != follower_count:
        logger.warning(
            "Follower count mismatch for author=%s post=%s: expected=%s actual=%s",
            author_id, post_id, follower_count, actual_count,
        )

    for follower_id in followers:
        send_single_notification.delay(follower_id, author_id, post_id, message)

    return {"notifications_sent": actual_count, "status": "processing"}


@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def send_verification_email(user_id, email, token):
    """Send email verification link"""
    subject = "Verify Your Email Address"
    verification_link = (
        f"{settings.FRONTEND_URL}/verify-email?token={token}&email={email}"
    )
    message = f"""
    Hello,

    Please click the link below to verify your email address:

    {verification_link}

    This link expires in 24 hours.

    If you did not create an account, please ignore this email.

    Thank you,
    Social Media Team
    """
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
    return f"Verification email sent to {email}"


@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def send_password_reset_email(user_id, email, token):
    """Send password reset link"""
    subject = "Password Reset Request"
    reset_link = (
        f"{settings.FRONTEND_URL}/password-reset-confirm?token={token}&email={email}"
    )
    message = f"""
    Hello,

    We received a request to reset your password.

    Click the link below to reset your password:

    {reset_link}

    This link expires in 1 hour.

    If you did not request this, please ignore this email.

    Thank you,
    Social Media Team
    """
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
    return f"Password reset email sent to {email}"


@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def send_welcome_email(user_id, email, username):
    """Send welcome email after verification"""
    subject = "Welcome to Social Media Platform!"
    message = f"""
    Hello {username},

    Welcome to Social Media Platform!

    Your account has been verified. You can now:
    - Create and share posts
    - Connect with friends
    - Send messages

    Get started by completing your profile.

    Thank you for joining us!

    Best regards,
    Social Media Team
    """
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
    return f"Welcome email sent to {email}"


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def create_follow_notification(self, following_id, follower_id):
    try:
        Notification.objects.create(
            recipient_id=following_id,  # user2 receives notification
            sender_id=follower_id,  # user1 is the sender
            notification_type="follow",
            message="started following you",
        )
    except Exception as exc:
        logger.exception(
            "Failed to create follow notification: following=%s follower=%s",
            following_id, follower_id,
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def create_like_notification(self, post_owner_id, liker_id, post_id):
    try:
        Notification.objects.create(
            recipient_id=post_owner_id,
            sender_id=liker_id,
            notification_type="like",
            message="liked your post",
        )
    except Exception as exc:
        logger.exception(
            "Failed to create like notification: post_owner=%s liker=%s post=%s",
            post_owner_id, liker_id, post_id,
        )
        raise self.retry(exc=exc)