"""
URL routing for the bookings app.

Supports both versioned and unversioned endpoints for backward compatibility.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Booking endpoints
    path("bookings/", views.create_booking, name="create-booking"),

    # LSA Search endpoints
    path("lsas/search/", views.search_lsas, name="search-lsas"),

    # Payment webhook (versioned)
    path("payments/webhook/", views.payment_webhook, name="payment-webhook-v1"),

    # Payment webhook (unversioned - for backward compatibility)
    path("payments/webhook/", views.payment_webhook, name="payment-webhook"),
]
