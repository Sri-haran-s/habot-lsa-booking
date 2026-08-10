"""
Tests for the Payment Service layer.
"""
import pytest
from unittest.mock import Mock, patch
from requests.exceptions import Timeout, ConnectionError, HTTPError

from apps.bookings.services.payment_service import (
    PaymentService,
    PaymentTimeoutError,
    PaymentConnectionError,
    PaymentHTTPError,
    PaymentResponseError,
)


class TestPaymentService:
    """Test the external payment service integration."""

    @pytest.fixture
    def service(self):
        return PaymentService(base_url="https://mock-payment.test/api")

    @patch("apps.bookings.services.payment_service.requests.Session.post")
    def test_process_payment_success(self, mock_post, service):
        """Test successful payment processing."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"id": "txn_123", "status": "completed"}
        mock_post.return_value = mock_response

        result = service.process_payment(booking_id=1, amount=100.00)

        assert result["success"] is True
        assert result["transaction_id"] == "txn_123"
        assert result["status"] == "completed"

    @patch("apps.bookings.services.payment_service.requests.Session.post")
    def test_process_payment_timeout(self, mock_post, service):
        """Test timeout exception handling."""
        mock_post.side_effect = Timeout("Connection timed out")

        with pytest.raises(PaymentTimeoutError):
            service.process_payment(booking_id=1, amount=100.00)

    @patch("apps.bookings.services.payment_service.requests.Session.post")
    def test_process_payment_connection_error(self, mock_post, service):
        """Test connection error handling."""
        mock_post.side_effect = ConnectionError("Connection refused")

        with pytest.raises(PaymentConnectionError):
            service.process_payment(booking_id=1, amount=100.00)

    @patch("apps.bookings.services.payment_service.requests.Session.post")
    def test_process_payment_http_error(self, mock_post, service):
        """Test HTTP error (4xx/5xx) handling."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("500 Internal Server Error")
        mock_post.return_value = mock_response

        with pytest.raises(PaymentHTTPError):
            service.process_payment(booking_id=1, amount=100.00)

    @patch("apps.bookings.services.payment_service.requests.Session.post")
    def test_process_payment_invalid_json(self, mock_post, service):
        """Test invalid JSON response handling."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        with pytest.raises(PaymentResponseError):
            service.process_payment(booking_id=1, amount=100.00)

    @patch("apps.bookings.services.payment_service.requests.Session.post")
    def test_process_payment_unexpected_response_format(self, mock_post, service):
        """Test unexpected response format handling."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = "not_a_dict"  # String instead of dict
        mock_post.return_value = mock_response

        with pytest.raises(PaymentResponseError):
            service.process_payment(booking_id=1, amount=100.00)
