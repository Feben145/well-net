"""Well-Net URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/auth/",      include("users.urls")),
    path("api/v1/foods/",     include("foods.urls")),
    path("api/v1/wellness/",  include("wellness.urls")),
    path("api/v1/ai/",        include("ai.urls")),
    path("api/v1/experts/",   include("experts.urls")),
    path("api/v1/packages/",  include("packages.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/community/", include("community.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



