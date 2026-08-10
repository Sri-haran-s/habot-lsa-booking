"""
Database models for the LSA Service Booking module.

Design Decisions:
- Skills stored as ArrayField (PostgreSQL-specific) for simplicity in a 4-6 hour project.
  Trade-off: Less normalized than a separate Skill model, but avoids join complexity
  and is perfectly suitable for filtering with PostgreSQL's array operators.
  In production with 1000+ skills, a normalized M2M Skill model would be better.
- Timezone-aware DateTimeField used throughout (USE_TZ=True).
- Database indexes on frequently queried fields: lsa, start_time, end_time, status.
- Unique constraint prevents exact duplicate bookings at DB level.
- Composite index on (lsa, start_time, end_time) optimizes overlap queries.
"""
import logging
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

logger = logging.getLogger("apps.bookings")


class Parent(models.Model):
    """Represents a parent seeking LSA services for their child."""

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "parents"
        ordering = ["-created_at"]
        verbose_name = "Parent"
        verbose_name_plural = "Parents"

    def __str__(self):
        return f"{self.name} ({self.email})"


class LSAProfile(models.Model):
    """Represents a Learning Support Assistant profile."""

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    # Using ArrayField for skills - PostgreSQL native, efficient for this scope
    # Trade-off: Less normalized but simpler and performant for moderate skill counts
    skills = models.JSONField(default=list, help_text="List of skill strings, e.g., ['Python', 'Autism Support']")
    experience_years = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lsa_profiles"
        ordering = ["-created_at"]
        verbose_name = "LSA Profile"
        verbose_name_plural = "LSA Profiles"
        indexes = [
            # GIN index for JSONField skills filtering (PostgreSQL)
            models.Index(fields=["is_active"], name="lsa_active_idx"),
        ]

    def __str__(self):
        return f"{self.name} - {', '.join(self.skills[:3])}"


class BookingRequest(models.Model):
    """Represents a booking request between a Parent and an LSA."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        related_name="bookings",
        db_index=True,
    )
    lsa = models.ForeignKey(
        LSAProfile,
        on_delete=models.CASCADE,
        related_name="bookings",
        db_index=True,
    )
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "booking_requests"
        ordering = ["-created_at"]
        verbose_name = "Booking Request"
        verbose_name_plural = "Booking Requests"
        constraints = [
            # Prevent exact duplicate bookings at database level
            models.UniqueConstraint(
                fields=["parent", "lsa", "start_time", "end_time"],
                name="unique_booking_slot",
            ),
            # Ensure start_time is strictly before end_time
            models.CheckConstraint(
                check=models.Q(start_time__lt=models.F("end_time")),
                name="start_before_end",
            ),
        ]
        indexes = [
            # Composite index for overlap queries - critical for performance
            models.Index(fields=["lsa", "start_time", "end_time"], name="booking_overlap_idx"),
            # Index for status-based filtering
            models.Index(fields=["status", "created_at"], name="booking_status_created_idx"),
        ]

    def clean(self):
        """Validate the booking before saving."""
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

        # Ensure timezone-aware datetimes
        if timezone.is_naive(self.start_time):
            self.start_time = timezone.make_aware(self.start_time)
        if timezone.is_naive(self.end_time):
            self.end_time = timezone.make_aware(self.end_time)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking #{self.id}: {self.parent.name} -> {self.lsa.name} ({self.start_time} to {self.end_time})"

    @classmethod
    def has_overlap(cls, lsa_id, start_time, end_time, exclude_id=None):
        """
        Check if the given time range overlaps with any existing active booking.

        Overlap condition:
        existing.start_time < requested.end_time 
        AND 
        existing.end_time > requested.start_time

        This correctly handles:
        - Partial overlaps (10:30-11:30 when 10:00-11:00 exists)
        - Complete containment (10:15-10:45 when 10:00-11:00 exists)
        - Exact match (10:00-11:00 when 10:00-11:00 exists)
        - Adjacent bookings are ALLOWED (10:00-11:00 and 11:00-12:00)
        """
        queryset = cls.objects.filter(
            lsa_id=lsa_id,
            status__in=[cls.Status.PENDING, cls.Status.CONFIRMED],
        ).filter(
            start_time__lt=end_time,
            end_time__gt=start_time,
        )

        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        return queryset.exists()
