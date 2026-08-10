"""
URL configuration for habot_backend project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.bookings.urls")),
    path("api/", include("apps.bookings.urls")),  # Unversioned fallback
]
