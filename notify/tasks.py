from celery import shared_task
from django.contrib.auth import get_user_model
from .models import Notification
from interactions.models import Follow
from django.core.mail import send_mail
from django.conf import settings

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


@shared_task
def send_verification_email(user_id, email, token):
    """Send email verification link"""
    subject = "Verify Your Email Address"
    verification_link = (
        f"http://127.0.0.1:8000/api/auth/verify-email/?token={token}&email={email}"
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


@shared_task
def send_password_reset_email(user_id, email, token):
    """Send password reset link"""
    subject = "Password Reset Request"
    reset_link = f"http://127.0.0.1:8000/api/auth/password-reset-confirm/?token={token}&email={email}"
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


@shared_task
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


@shared_task
def create_follow_notification(following_id, follower_id):
    try:
        Notification.objects.create(
            recipient_id=following_id,  # user2 receives notification
            sender_id=follower_id,  # user1 is the sender
            notification_type="follow",
            message="started following you",
        )
    except Exception as e:
        print(f"Failed: {e}")


@shared_task
def create_like_notification(post_owner_id, liker_id, post_id):
    try:
        Notification.objects.create(
            recipient_id=post_owner_id,
            sender_id=liker_id,
            notification_type="like",
            message="liked your post",
        )
    except Exception as e:
        print(f"Failed: {e}")
