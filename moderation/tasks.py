from celery import shared_task
from posts.models import Post

PROHIBITED_WORDS = ["spam", "hate", "violence", "abuse", "scam"]


@shared_task
def check_post_toxicity(post_id, content):
    """Background task to check post for inappropriate content"""
    try:
        is_toxic = False
        reasons = []

        content_lower = content.lower()
        for word in PROHIBITED_WORDS:
            if word in content_lower:
                is_toxic = True
                reasons.append(f"Contains: {word}")

        post = Post.objects.get(id=post_id)
        post.is_flagged = is_toxic
        post.moderation_reasons = ", ".join(reasons) if reasons else None

        if is_toxic:
            post.is_active = False

        post.save()

        return {"post_id": post_id, "is_toxic": is_toxic}
    except Exception as e:
        return {"post_id": post_id, "error": str(e)}
