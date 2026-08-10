"""
API Views for the LSA Booking module.

Architecture: Django MVT (Model-View-Template) adapted for REST APIs via DRF.
- Models: Data layer (models.py)
- Views: Business logic + HTTP handling (this file)
- Templates: Replaced by DRF Serializers for JSON rendering

This is Django's MVT pattern where "View" handles both business logic and HTTP,
with DRF providing the serialization/presentation layer.
"""
import logging
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError

from .models import Parent, LSAProfile, BookingRequest
from .serializers import BookingRequestSerializer, LSAProfileSerializer
from .services.payment_service import (
    PaymentService,
    PaymentServiceError,
)

logger = logging.getLogger("apps.bookings")


# =============================================================================
# BOOKING API
# =============================================================================

@api_view(["POST"])
def create_booking(request):
    """
    POST /api/v1/bookings/

    Creates a new booking request with validation and double-booking prevention.

    Request Body:
        {
            "parent_id": 1,
            "lsa_id": 1,
            "start_time": "2026-08-12T10:00:00Z",
            "end_time": "2026-08-12T11:00:00Z"
        }

    Responses:
        201: Booking created successfully
        400: Validation error (invalid input, overlapping booking)
        404: Parent or LSA not found
    """
    serializer = BookingRequestSerializer(data=request.data)

    if not serializer.is_valid():
        logger.warning(f"Booking validation failed: {serializer.errors}")
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        booking = serializer.save()
        return Response(
            {
                "success": True,
                "message": "Booking created successfully",
                "data": BookingRequestSerializer(booking).data,
            },
            status=status.HTTP_201_CREATED,
        )
    except DRFValidationError as e:
        logger.warning(f"Booking creation failed: {e.detail}")
        return Response(
            {"success": False, "errors": e.detail},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Unexpected error creating booking: {e}")
        return Response(
            {"success": False, "errors": "An unexpected error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =============================================================================
# LSA SEARCH API
# =============================================================================

@api_view(["GET"])
def search_lsas(request):
    """
    GET /api/v1/lsas/search/?skill=Python&skill=Autism+Support

    Search available LSAs filtered by skills.
    Only returns active LSAs.

    Query Parameters:
        skill: Skill to filter by (can be repeated for multiple skills)

    Responses:
        200: List of matching LSAs
        400: Invalid query parameters

    Optimization:
    - Uses JSONField contains lookup for skill filtering (PostgreSQL)
    - No N+1 problem: LSAProfile has no FK relations that would trigger extra queries
    - If we added related data, we would use select_related/prefetch_related
    """
    skills = request.query_params.getlist("skill")

    # Validate query parameters
    if skills:
        # Clean and validate skill strings
        skills = [s.strip() for s in skills if s.strip()]
        if not skills:
            return Response(
                {"success": False, "errors": {"skill": "Skill parameter cannot be empty."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Base queryset: only active LSAs
    queryset = LSAProfile.objects.filter(is_active=True)

    # Filter by skills
    # PostgreSQL: uses JSON containment operator @> (skills__contains=[skill])
    # SQLite fallback: string-based filtering for local development/testing
    if skills:
        from django.db import connection
        is_postgres = connection.vendor == "postgresql"

        # Match LSAs that have ALL requested skills
        for skill in skills:
            if is_postgres:
                queryset = queryset.filter(skills__contains=[skill])
            else:
                # SQLite fallback: case-insensitive string match on JSON representation
                queryset = queryset.filter(skills__icontains=skill)

    # Order by experience (most experienced first)
    queryset = queryset.order_by("-experience_years", "name")

    # Serialize
    serializer = LSAProfileSerializer(queryset, many=True)

    return Response(
        {
            "success": True,
            "count": len(serializer.data),
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


# =============================================================================
# PAYMENT WEBHOOK
# =============================================================================

@api_view(["POST"])
def payment_webhook(request):
    """
    POST /api/v1/payments/webhook/
    POST /api/payments/webhook/ (unversioned compatibility)

    Handles payment success/failure webhooks from external payment gateway.

    Request Body:
        {
            "booking_id": 1,
            "payment_status": "success",
            "transaction_id": "txn_123"
        }

    State Transitions:
        PENDING + success -> CONFIRMED
        PENDING + failure -> FAILED

    Idempotency:
        - Already CONFIRMED bookings are ignored (return 200)
        - Already FAILED bookings reject new webhooks (return 400)
        - Duplicate success webhooks are handled gracefully

    Responses:
        200: Webhook processed successfully
        400: Invalid payload or invalid state transition
        404: Booking not found
    """
    data = request.data

    # Validate required fields
    booking_id = data.get("booking_id")
    payment_status = data.get("payment_status")
    transaction_id = data.get("transaction_id")

    if not booking_id:
        logger.warning("Webhook received without booking_id")
        return Response(
            {"success": False, "errors": {"booking_id": "This field is required."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not payment_status:
        logger.warning(f"Webhook received for booking {booking_id} without payment_status")
        return Response(
            {"success": False, "errors": {"payment_status": "This field is required."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Normalize payment status
    payment_status = str(payment_status).lower().strip()

    if payment_status not in ("success", "failure", "failed"):
        logger.warning(f"Webhook received with invalid payment_status: {payment_status}")
        return Response(
            {"success": False, "errors": {"payment_status": "Must be 'success' or 'failure'."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            # Use select_for_update to prevent race conditions
            try:
                booking = BookingRequest.objects.select_for_update().get(id=booking_id)
            except BookingRequest.DoesNotExist:
                logger.warning(f"Webhook received for non-existent booking: {booking_id}")
                return Response(
                    {"success": False, "errors": {"booking_id": "Booking not found."}},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Idempotency: already confirmed
            if booking.status == BookingRequest.Status.CONFIRMED:
                logger.info(f"Duplicate webhook ignored for already confirmed booking {booking_id}")
                return Response(
                    {
                        "success": True,
                        "message": "Booking already confirmed.",
                        "data": {"booking_id": booking_id, "status": booking.status},
                    },
                    status=status.HTTP_200_OK,
                )

            # Invalid transition: cannot process webhook for cancelled bookings
            if booking.status == BookingRequest.Status.CANCELLED:
                logger.warning(f"Webhook rejected for cancelled booking {booking_id}")
                return Response(
                    {"success": False, "errors": {"detail": "Cannot process payment for cancelled booking."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Invalid transition: already failed, cannot re-process
            if booking.status == BookingRequest.Status.FAILED:
                logger.warning(f"Webhook rejected for already failed booking {booking_id}")
                return Response(
                    {"success": False, "errors": {"detail": "Booking already marked as failed."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Process state transition
            if payment_status in ("failure", "failed"):
                booking.status = BookingRequest.Status.FAILED
                booking.save(update_fields=["status", "updated_at"])
                logger.info(f"Booking {booking_id} marked as FAILED (txn: {transaction_id})")
                return Response(
                    {
                        "success": True,
                        "message": "Payment failed. Booking marked as failed.",
                        "data": {"booking_id": booking_id, "status": booking.status},
                    },
                    status=status.HTTP_200_OK,
                )

            # Success transition
            booking.status = BookingRequest.Status.CONFIRMED
            booking.save(update_fields=["status", "updated_at"])
            logger.info(f"Booking {booking_id} confirmed (txn: {transaction_id})")
            return Response(
                {
                    "success": True,
                    "message": "Payment successful. Booking confirmed.",
                    "data": {"booking_id": booking_id, "status": booking.status},
                },
                status=status.HTTP_200_OK,
            )

    except Exception as e:
        logger.error(f"Unexpected error processing webhook for booking {booking_id}: {e}")
        return Response(
            {"success": False, "errors": "An unexpected error occurred processing the webhook."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
