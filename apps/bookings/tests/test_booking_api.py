"""
Tests for the Booking API endpoints.
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.bookings.models import Parent, LSAProfile, BookingRequest


@pytest.mark.django_db
class TestBookingAPI:
    """Test POST /api/v1/bookings/ endpoint."""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def parent(self):
        return Parent.objects.create(
            name="Test Parent",
            email="parent@test.com",
        )

    @pytest.fixture
    def lsa(self):
        return LSAProfile.objects.create(
            name="Test LSA",
            email="lsa@test.com",
            skills=["Python"],
            is_active=True,
        )

    def test_create_booking_success(self, client, parent, lsa):
        """Test 201 response for valid booking creation."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        response = client.post(
            reverse("create-booking"),
            data={
                "parent_id": parent.id,
                "lsa_id": lsa.id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["status"] == BookingRequest.Status.PENDING
        assert response.data["data"]["parent"]["id"] == parent.id
        assert response.data["data"]["lsa"]["id"] == lsa.id

    def test_create_booking_invalid_parent(self, client, lsa):
        """Test 400 response for non-existent parent."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        response = client.post(
            reverse("create-booking"),
            data={
                "parent_id": 99999,
                "lsa_id": lsa.id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_create_booking_invalid_lsa(self, client, parent):
        """Test 400 response for non-existent LSA."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        response = client.post(
            reverse("create-booking"),
            data={
                "parent_id": parent.id,
                "lsa_id": 99999,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_create_booking_invalid_time_range(self, client, parent, lsa):
        """Test 400 response when start_time >= end_time."""
        start = timezone.now() + timedelta(days=1)
        end = start - timedelta(hours=1)  # Invalid: end before start

        response = client.post(
            reverse("create-booking"),
            data={
                "parent_id": parent.id,
                "lsa_id": lsa.id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_create_booking_double_booking(self, client, parent, lsa):
        """Test 400 response for overlapping booking (double booking prevention)."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        # Create first booking
        response1 = client.post(
            reverse("create-booking"),
            data={
                "parent_id": parent.id,
                "lsa_id": lsa.id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            format="json",
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Attempt overlapping booking
        response2 = client.post(
            reverse("create-booking"),
            data={
                "parent_id": parent.id,
                "lsa_id": lsa.id,
                "start_time": (start + timedelta(minutes=30)).isoformat(),
                "end_time": (end + timedelta(minutes=30)).isoformat(),
            },
            format="json",
        )

        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert response2.data["success"] is False
        assert "already booked" in str(response2.data["errors"]).lower()

    def test_create_booking_back_to_back_allowed(self, client, parent, lsa):
        """Test that back-to-back bookings are allowed."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        # First booking: 10:00-11:00
        response1 = client.post(
            reverse("create-booking"),
            data={
                "parent_id": parent.id,
                "lsa_id": lsa.id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            format="json",
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Second booking: 11:00-12:00 (should be allowed)
        response2 = client.post(
            reverse("create-booking"),
            data={
                "parent_id": parent.id,
                "lsa_id": lsa.id,
                "start_time": end.isoformat(),
                "end_time": (end + timedelta(hours=1)).isoformat(),
            },
            format="json",
        )

        assert response2.status_code == status.HTTP_201_CREATED
        assert response2.data["success"] is True
