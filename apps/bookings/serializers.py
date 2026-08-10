"""
DRF Serializers for the LSA Booking module.
"""
import logging
from django.utils import timezone
from rest_framework import serializers
from .models import Parent, LSAProfile, BookingRequest

logger = logging.getLogger("apps.bookings")


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = ["id", "name", "email", "phone", "created_at"]


class LSAProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LSAProfile
        fields = ["id", "name", "email", "skills", "experience_years", "is_active", "created_at"]


class BookingRequestSerializer(serializers.ModelSerializer):
    parent = ParentSerializer(read_only=True)
    lsa = LSAProfileSerializer(read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Parent.objects.all(),
        source="parent",
        write_only=True,
    )
    lsa_id = serializers.PrimaryKeyRelatedField(
        queryset=LSAProfile.objects.all(),
        source="lsa",
        write_only=True,
    )

    class Meta:
        model = BookingRequest
        fields = [
            "id",
            "parent",
            "lsa",
            "parent_id",
            "lsa_id",
            "start_time",
            "end_time",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "created_at", "updated_at"]

    def validate(self, data):
        """Cross-field validation for booking requests."""
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        # Validate time range
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError(
                    {"end_time": "End time must be after start time."}
                )

            # Ensure timezone-aware
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time)
            if timezone.is_naive(end_time):
                end_time = timezone.make_aware(end_time)

            # Prevent bookings in the past (business rule)
            if start_time < timezone.now():
                raise serializers.ValidationError(
                    {"start_time": "Cannot create bookings in the past."}
                )

        return data

    def create(self, validated_data):
        """Create booking with overlap check inside transaction."""
        from django.db import transaction

        lsa = validated_data["lsa"]
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]

        # Use select_for_update to prevent race conditions on the LSA's bookings
        with transaction.atomic():
            # Lock the LSA row to prevent concurrent bookings
            locked_lsa = (
                LSAProfile.objects.select_for_update()
                .get(id=lsa.id)
            )

            # Check for overlapping bookings
            if BookingRequest.has_overlap(lsa.id, start_time, end_time):
                logger.warning(
                    f"Double booking attempt for LSA {lsa.id} "
                    f"from {start_time} to {end_time}"
                )
                raise serializers.ValidationError(
                    {"detail": "This LSA is already booked for the requested time slot."}
                )

            booking = BookingRequest.objects.create(**validated_data)
            logger.info(f"Booking created: {booking.id} for LSA {lsa.id}")
            return booking
