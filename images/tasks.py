import boto3
from io import BytesIO
from PIL import Image
from celery import shared_task
from django.conf import settings


@shared_task
def process_uploaded_image(image_data, user_id, post_id):
    """
    Process image in background: compress, create thumbnails, upload to S3
    User gets immediate "Processing" response.
    """
    try:
        # Open image from bytes
        img = Image.open(BytesIO(image_data))

        # Create thumbnail (150x150)
        img.thumbnail((150, 150))
        thumb_buffer = BytesIO()
        img.save(thumb_buffer, format="JPEG", quality=85)

        # Compress original (max 1024px width)
        img = Image.open(BytesIO(image_data))
        if img.width > 1024:
            ratio = 1024 / img.width
            new_size = (1024, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        compressed_buffer = BytesIO()
        img.save(compressed_buffer, format="JPEG", quality=75)

        # Upload to S3 (or local storage for development)
        if settings.USE_S3:
            s3 = boto3.client("s3")
            s3.upload_fileobj(
                compressed_buffer,
                settings.AWS_STORAGE_BUCKET_NAME,
                f"posts/{post_id}/original.jpg",
            )
            s3.upload_fileobj(
                thumb_buffer,
                settings.AWS_STORAGE_BUCKET_NAME,
                f"posts/{post_id}/thumbnail.jpg",
            )

        # Update post with image URLs
        from posts.models import Post

        post = Post.objects.get(id=post_id)
        post.image_url = f"/media/posts/{post_id}/original.jpg"
        post.thumbnail_url = f"/media/posts/{post_id}/thumbnail.jpg"
        post.image_processed = True
        post.save()

        return {"status": "completed", "post_id": post_id}

    except Exception as e:
        print(f"Image processing failed: {e}")
        return {"status": "failed", "error": str(e)}
