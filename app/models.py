"""Internal API models for normalized Razorpay order data."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class NormalizedOrder(BaseModel):
    """Stable application representation of a Razorpay order."""

    id: str
    amount: int = Field(description="Amount in the smallest currency unit.")
    currency: str
    receipt: Optional[str] = None
    status: str
    created_at: datetime


class OrdersResponse(BaseModel):
    """Orders returned by FinGraph, never Razorpay's raw payload."""

    count: int
    orders: List[NormalizedOrder]
