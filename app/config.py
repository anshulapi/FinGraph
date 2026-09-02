"""Configuration loading for Razorpay Test Mode."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(ValueError):
    """Raised when required, safe-to-report configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Secrets must never be rendered or logged."""

    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_api_base_url: str = "https://api.razorpay.com/v1"

    @classmethod
    def from_environment(cls) -> "Settings":
        key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

        if not key_id or not key_secret:
            raise ConfigurationError(
                "Razorpay Test Mode credentials are not configured. "
                "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
            )
        if not key_id.startswith("rzp_test_"):
            raise ConfigurationError("RAZORPAY_KEY_ID must be a Razorpay Test Mode key.")

        return cls(razorpay_key_id=key_id, razorpay_key_secret=key_secret)
