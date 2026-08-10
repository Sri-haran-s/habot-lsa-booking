"""
Tests for database models and business logic.
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from apps.bookings.models import Parent, LSAProfile, BookingRequest


@pytest.mark.django_db
class TestBookingRequestModel:
    """Test the BookingRequest model and overlap logic."""

    @pytest.fixture
    def parent(self):
        return Parent.objects.create(
            name="Test Parent",
            email="parent@test.com",
            phone="+1234567890",
        )

    @pytest.fixture
    def lsa(self):
        return LSAProfile.objects.create(
            name="Test LSA",
            email="lsa@test.com",
            skills=["Python", "Autism Support"],
            experience_years=5,
            is_active=True,
        )

    def test_create_booking_success(self, parent, lsa):
        """Test successful booking creation."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        booking = BookingRequest.objects.create(
            parent=parent,
            lsa=lsa,
            start_time=start,
            end_time=end,
        )

        assert booking.id is not None
        assert booking.status == BookingRequest.Status.PENDING
        assert booking.start_time < booking.end_time

    def test_booking_start_after_end_raises_error(self, parent, lsa):
        """Test that start_time >= end_time raises ValidationError."""
        start = timezone.now() + timedelta(days=1)
        end = start - timedelta(hours=1)  # end before start

        with pytest.raises(Exception):  # ValidationError or IntegrityError
            BookingRequest.objects.create(
                parent=parent,
                lsa=lsa,
                start_time=start,
                end_time=end,
            )

    def test_overlap_detection_exact_match(self, parent, lsa):
        """Test that exact time match is detected as overlap."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        BookingRequest.objects.create(
            parent=parent,
            lsa=lsa,
            start_time=start,
            end_time=end,
            status=BookingRequest.Status.CONFIRMED,
        )

        assert BookingRequest.has_overlap(lsa.id, start, end) is True

    def test_overlap_detection_partial_overlap(self, parent, lsa):
        """Test partial overlap detection."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        BookingRequest.objects.create(
            parent=parent,
            lsa=lsa,
            start_time=start,
            end_time=end,
            status=BookingRequest.Status.CONFIRMED,
        )

        # 10:30-11:30 overlaps with 10:00-11:00
        new_start = start + timedelta(minutes=30)
        new_end = end + timedelta(minutes=30)
        assert BookingRequest.has_overlap(lsa.id, new_start, new_end) is True

    def test_overlap_detection_containment(self, parent, lsa):
        """Test that contained booking is detected as overlap."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        BookingRequest.objects.create(
            parent=parent,
            lsa=lsa,
            start_time=start,
            end_time=end,
            status=BookingRequest.Status.CONFIRMED,
        )

        # 10:15-10:45 is contained within 10:00-11:00
        new_start = start + timedelta(minutes=15)
        new_end = end - timedelta(minutes=15)
        assert BookingRequest.has_overlap(lsa.id, new_start, new_end) is True

    def test_no_overlap_back_to_back(self, parent, lsa):
        """Test that back-to-back bookings are allowed."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        BookingRequest.objects.create(
            parent=parent,
            lsa=lsa,
            start_time=start,
            end_time=end,
            status=BookingRequest.Status.CONFIRMED,
        )

        # 11:00-12:00 does NOT overlap with 10:00-11:00
        new_start = end
        new_end = end + timedelta(hours=1)
        assert BookingRequest.has_overlap(lsa.id, new_start, new_end) is False

    def test_no_overlap_cancelled_booking(self, parent, lsa):
        """Test that cancelled bookings don't block new bookings."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        BookingRequest.objects.create(
            parent=parent,
            lsa=lsa,
            start_time=start,
            end_time=end,
            status=BookingRequest.Status.CANCELLED,
        )

        # Cancelled booking should not prevent new booking
        assert BookingRequest.has_overlap(lsa.id, start, end) is False
