"""
Tests for the Payment Webhook endpoint.
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.bookings.models import Parent, LSAProfile, BookingRequest


@pytest.mark.django_db
class TestPaymentWebhook:
    """Test POST /api/v1/payments/webhook/ endpoint."""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def confirmed_booking(self):
        parent = Parent.objects.create(name="Parent", email="p@test.com")
        lsa = LSAProfile.objects.create(name="LSA", email="l@test.com", skills=["Python"])
        return BookingRequest.objects.create(
            parent=parent,
            lsa=lsa,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            status=BookingRequest.Status.PENDING,
        )

    def test_webhook_success_confirms_booking(self, client, confirmed_booking):
        """Test successful payment webhook transitions PENDING -> CONFIRMED."""
        response = client.post(
            reverse("payment-webhook-v1"),
            data={
                "booking_id": confirmed_booking.id,
                "payment_status": "success",
                "transaction_id": "txn_123",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["status"] == BookingRequest.Status.CONFIRMED

        # Verify database state
        confirmed_booking.refresh_from_db()
        assert confirmed_booking.status == BookingRequest.Status.CONFIRMED

    def test_webhook_failure_marks_booking_failed(self, client, confirmed_booking):
        """Test failed payment webhook transitions PENDING -> FAILED."""
        response = client.post(
            reverse("payment-webhook-v1"),
            data={
                "booking_id": confirmed_booking.id,
                "payment_status": "failure",
                "transaction_id": "txn_456",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["status"] == BookingRequest.Status.FAILED

        confirmed_booking.refresh_from_db()
        assert confirmed_booking.status == BookingRequest.Status.FAILED

    def test_webhook_idempotent_already_confirmed(self, client, confirmed_booking):
        """Test duplicate success webhook for already confirmed booking is idempotent."""
        # First, confirm the booking
        confirmed_booking.status = BookingRequest.Status.CONFIRMED
        confirmed_booking.save()

        response = client.post(
            reverse("payment-webhook-v1"),
            data={
                "booking_id": confirmed_booking.id,
                "payment_status": "success",
                "transaction_id": "txn_789",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "already confirmed" in response.data["message"].lower()

    def test_webhook_invalid_already_failed(self, client, confirmed_booking):
        """Test webhook rejected for already failed booking."""
        confirmed_booking.status = BookingRequest.Status.FAILED
        confirmed_booking.save()

        response = client.post(
            reverse("payment-webhook-v1"),
            data={
                "booking_id": confirmed_booking.id,
                "payment_status": "success",
                "transaction_id": "txn_999",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_webhook_invalid_payload(self, client):
        """Test 400 response for missing required fields."""
        response = client.post(
            reverse("payment-webhook-v1"),
            data={"payment_status": "success"},  # Missing booking_id
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_webhook_booking_not_found(self, client):
        """Test 404 response for non-existent booking."""
        response = client.post(
            reverse("payment-webhook-v1"),
            data={
                "booking_id": 99999,
                "payment_status": "success",
                "transaction_id": "txn_000",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["success"] is False

    def test_webhook_invalid_payment_status(self, client, confirmed_booking):
        """Test 400 response for invalid payment_status value."""
        response = client.post(
            reverse("payment-webhook-v1"),
            data={
                "booking_id": confirmed_booking.id,
                "payment_status": "invalid_status",
                "transaction_id": "txn_000",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False
