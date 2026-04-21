from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .tasks import process_uploaded_image


class UploadImageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"error": "No image provided"}, status=400)

        # Read image data
        image_data = image_file.read()

        # Queue background processing
        task = process_uploaded_image.delay(image_data, str(request.user.id), post_id)

        return Response(
            {
                "status": "processing",
                "task_id": task.id,
                "message": "Image is being processed. It will appear shortly.",
            },
            status=202,
        )  # 202 Accepted = "We got it, working on it"
