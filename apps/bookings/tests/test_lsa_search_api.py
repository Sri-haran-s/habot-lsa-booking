"""
Tests for the LSA Search API endpoint.
Includes N+1 query prevention verification.
"""
import pytest
from django.urls import reverse
from django.db import connection, reset_queries
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from apps.bookings.models import LSAProfile


@pytest.mark.django_db
class TestLSASearchAPI:
    """Test GET /api/v1/lsas/search/ endpoint."""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def lsas(self):
        """Create test LSAs with various skills."""
        lsas = []
        skills_data = [
            ["Python", "Autism Support"],
            ["Python", "Math"],
            ["Reading", "Autism Support"],
            ["Python", "Reading", "Math"],
        ]
        for i, skills in enumerate(skills_data):
            lsas.append(LSAProfile.objects.create(
                name=f"LSA {i+1}",
                email=f"lsa{i+1}@test.com",
                skills=skills,
                experience_years=i + 1,
                is_active=True,
            ))
        # Create inactive LSA
        LSAProfile.objects.create(
            name="Inactive LSA",
            email="inactive@test.com",
            skills=["Python"],
            is_active=False,
        )
        return lsas

    def test_search_by_single_skill(self, client, lsas):
        """Test filtering LSAs by a single skill."""
        response = client.get(
            reverse("search-lsas"),
            {"skill": "Python"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["count"] == 3  # 3 active LSAs have Python

        # Verify all returned LSAs have Python skill
        for lsa in response.data["data"]:
            assert "Python" in lsa["skills"]

    def test_search_by_multiple_skills(self, client, lsas):
        """Test filtering LSAs by multiple skills (AND logic)."""
        response = client.get(
            reverse("search-lsas"),
            {"skill": ["Python", "Autism Support"]},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1  # Only LSA 1 has both
        assert response.data["data"][0]["name"] == "LSA 1"

    def test_search_no_results(self, client, lsas):
        """Test search with skill that no LSA has."""
        response = client.get(
            reverse("search-lsas"),
            {"skill": "NonExistentSkill"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0
        assert response.data["data"] == []

    def test_search_excludes_inactive(self, client, lsas):
        """Test that inactive LSAs are not returned."""
        response = client.get(
            reverse("search-lsas"),
            {"skill": "Python"},
        )

        assert response.status_code == status.HTTP_200_OK
        # Inactive LSA has Python but should not appear
        for lsa in response.data["data"]:
            assert lsa["name"] != "Inactive LSA"

    def test_search_no_nplus1_queries(self, client, lsas):
        """
        CRITICAL TEST: Verify N+1 query problem is avoided.

        The N+1 problem occurs when:
        1 query fetches the main objects (LSAs)
        N additional queries fetch related data for each object

        Our LSAProfile model has no FK relationships, so there should be
        exactly 1 query regardless of result count.
        """
        settings.DEBUG = True
        reset_queries()

        response = client.get(
            reverse("search-lsas"),
            {"skill": "Python"},
        )

        query_count = len(connection.queries)

        # Should be exactly 1 query (no N+1)
        # If we had related objects, we'd verify select_related/prefetch_related
        assert query_count == 1, f"Expected 1 query, got {query_count}. N+1 problem detected!"

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

        settings.DEBUG = False
