"""Small reusable Razorpay Test Mode API client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import Settings
from app.models import NormalizedOrder


class RazorpayError(RuntimeError):
    """Base error that contains no secrets or raw provider payloads."""


class RazorpayAuthenticationError(RazorpayError):
    """Razorpay rejected the configured Test Mode credentials."""


class RazorpayNetworkError(RazorpayError):
    """Razorpay could not be reached."""


class RazorpayAPIError(RazorpayError):
    """Razorpay returned a non-authentication API error."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"Razorpay API request failed with status {status_code}.")
        self.status_code = status_code


def normalize_order(raw_order: Dict[str, Any]) -> NormalizedOrder:
    """Convert the Razorpay order schema to FinGraph's internal model."""
    try:
        created_at = datetime.fromtimestamp(int(raw_order["created_at"]), tz=timezone.utc)
        return NormalizedOrder(
            id=str(raw_order["id"]),
            amount=int(raw_order["amount"]),
            currency=str(raw_order["currency"]),
            receipt=raw_order.get("receipt"),
            status=str(raw_order["status"]),
            created_at=created_at,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RazorpayError("Razorpay returned an invalid order response.") from exc


class RazorpayClient:
    """Minimal client limited to reading orders from Razorpay Test Mode."""

    def __init__(self, settings: Settings, http_client: Optional[httpx.Client] = None) -> None:
        self._http_client = http_client or httpx.Client(
            base_url=settings.razorpay_api_base_url,
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
            timeout=httpx.Timeout(10.0),
        )
        self._owns_http_client = http_client is None

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def list_orders(self, *, count: int = 10, skip: int = 0) -> List[NormalizedOrder]:
        try:
            response = self._http_client.get("/orders", params={"count": count, "skip": skip})
        except httpx.RequestError as exc:
            raise RazorpayNetworkError("Unable to reach Razorpay Test Mode API.") from exc

        if response.status_code in (401, 403):
            raise RazorpayAuthenticationError("Razorpay rejected the Test Mode credentials.")
        if response.is_error:
            raise RazorpayAPIError(response.status_code)

        try:
            payload = response.json()
            items = payload["items"]
            if not isinstance(items, list):
                raise TypeError("items is not a list")
        except (KeyError, TypeError, ValueError) as exc:
            raise RazorpayError("Razorpay returned an invalid orders response.") from exc

        return [normalize_order(item) for item in items]
