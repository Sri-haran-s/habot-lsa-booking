"""
Payment Service Layer

Design Decision:
- External HTTP calls are isolated in this service layer, not in views.
- This keeps views focused on HTTP handling and makes the service testable.
- In production, this would call Stripe/PayPal APIs. Here we simulate with requests.
"""
import logging
import os
from typing import Dict, Any, Optional
import requests
from requests.exceptions import (
    Timeout,
    ConnectionError,
    HTTPError,
    RequestException,
)

logger = logging.getLogger("apps.bookings.services")

# Mock payment gateway configuration
MOCK_PAYMENT_BASE_URL = os.getenv(
    "MOCK_PAYMENT_URL", 
    "https://httpbin.org/post"  # Public test endpoint for demo
)
TIMEOUT_SECONDS = 10


class PaymentServiceError(Exception):
    """Base exception for payment service errors."""
    pass


class PaymentTimeoutError(PaymentServiceError):
    """Raised when payment gateway times out."""
    pass


class PaymentConnectionError(PaymentServiceError):
    """Raised when connection to payment gateway fails."""
    pass


class PaymentHTTPError(PaymentServiceError):
    """Raised when payment gateway returns HTTP error."""
    pass


class PaymentResponseError(PaymentServiceError):
    """Raised when payment gateway returns invalid response."""
    pass


class PaymentService:
    """Service for interacting with external payment providers."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = TIMEOUT_SECONDS):
        self.base_url = base_url or MOCK_PAYMENT_BASE_URL
        self.timeout = timeout
        self.session = requests.Session()
        # In production, configure auth headers, retries, etc.

    def process_payment(
        self,
        booking_id: int,
        amount: float,
        currency: str = "USD",
    ) -> Dict[str, Any]:
        """
        Process a payment for a booking.

        Args:
            booking_id: The booking ID to charge for
            amount: Amount to charge
            currency: Currency code (default USD)

        Returns:
            Dict containing transaction details

        Raises:
            PaymentTimeoutError: If gateway times out
            PaymentConnectionError: If connection fails
            PaymentHTTPError: If gateway returns 4xx/5xx
            PaymentResponseError: If response is invalid
        """
        payload = {
            "booking_id": booking_id,
            "amount": amount,
            "currency": currency,
        }

        try:
            logger.info(f"Initiating payment for booking {booking_id}, amount {amount} {currency}")

            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )

            # Raise for 4xx/5xx status codes
            response.raise_for_status()

            # Parse JSON response
            try:
                data = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON from payment gateway: {e}")
                raise PaymentResponseError("Invalid JSON response from payment gateway") from e

            # Validate expected response structure
            if not isinstance(data, dict):
                logger.error(f"Unexpected response type: {type(data)}")
                raise PaymentResponseError("Unexpected response format from payment gateway")

            logger.info(f"Payment processed successfully for booking {booking_id}")
            return {
                "success": True,
                "transaction_id": data.get("id", f"txn_{booking_id}"),
                "status": "completed",
                "raw_response": data,
            }

        except Timeout as e:
            logger.error(f"Payment gateway timeout for booking {booking_id}: {e}")
            raise PaymentTimeoutError("Payment gateway timed out") from e

        except ConnectionError as e:
            logger.error(f"Payment gateway connection error for booking {booking_id}: {e}")
            raise PaymentConnectionError("Failed to connect to payment gateway") from e

        except HTTPError as e:
            logger.error(f"Payment gateway HTTP error for booking {booking_id}: {e}")
            raise PaymentHTTPError(f"Payment gateway returned error: {e}") from e

        except RequestException as e:
            logger.error(f"Unexpected payment request error for booking {booking_id}: {e}")
            raise PaymentServiceError(f"Payment request failed: {e}") from e

    def verify_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Verify a transaction status with the payment gateway."""
        try:
            logger.info(f"Verifying transaction {transaction_id}")

            response = self.session.get(
                f"{self.base_url}/{transaction_id}",
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            return {
                "transaction_id": transaction_id,
                "verified": True,
                "status": data.get("status", "unknown"),
            }

        except (Timeout, ConnectionError, HTTPError, RequestException) as e:
            logger.error(f"Transaction verification failed for {transaction_id}: {e}")
            return {
                "transaction_id": transaction_id,
                "verified": False,
                "status": "error",
                "error": str(e),
            }
