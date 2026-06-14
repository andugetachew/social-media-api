from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import permissions
from django.http import JsonResponse
from django.views.generic import RedirectView

def health_check(request):
    return JsonResponse({"status": "ok"})
urlpatterns = [
    path("", RedirectView.as_view(url="/api/docs/"), name="root"),
     path("health/", health_check, name="health"), 
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/auth/", include("accounts.urls")),
    path("api/posts/", include("posts.urls")),
    path("api/interactions/", include("interactions.urls")),
    path("api/comments/", include("comments.urls")),
    path("api/notifications/", include("notify.urls")),
    path(
        "api/password_reset/",
        include("django_rest_passwordreset.urls", namespace="password_reset"),
    ),
    path("api/chat/", include("chat.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
