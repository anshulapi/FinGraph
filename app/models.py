"""Internal API models for normalized Razorpay order data."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

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


class Opportunity(BaseModel):
    """A deterministic, order-level merchant opportunity."""

    opportunity_type: Literal["high_value_order"]
    source_order_id: str
    currency: str
    observed_amount: int = Field(description="Observed order amount in the smallest currency unit.")
    baseline_amount: float = Field(description="Median order amount for the same currency.")
    uplift_ratio: float = Field(description="Amount above the median, expressed as a ratio.")
    explanation: str


class OpportunitiesResponse(BaseModel):
    """Deterministic opportunities derived from normalized orders."""

    count: int
    opportunities: List[Opportunity]
