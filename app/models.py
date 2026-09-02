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


class HighValueOrderReviewParameters(BaseModel):
    """Evidence required for a non-executing high-value-order review."""

    source_order_id: str
    currency: str
    observed_amount: int
    baseline_amount: float
    uplift_ratio: float


class StrategyAction(BaseModel):
    """A typed action proposal that remains non-executing at this milestone."""

    action_type: Literal["review_high_value_order"]
    parameters: HighValueOrderReviewParameters


class Strategy(BaseModel):
    """A deterministic, review-only response to an opportunity."""

    opportunity: Opportunity
    proposed_action: StrategyAction
    reasoning: str
    expected_outcome: str
    confidence: Literal["low"]
    confidence_rationale: str


class StrategiesResponse(BaseModel):
    """Strategies derived from deterministic opportunities."""

    count: int
    strategies: List[Strategy]


PolicyDecisionStatus = Literal["ALLOW", "BLOCK"]


class PolicyEvidence(BaseModel):
    """Typed strategy fields evaluated by the deterministic policy gate."""

    action_type: str
    source_order_id: str
    currency: str
    observed_amount: int
    baseline_amount: float
    uplift_ratio: float
    maximum_allowed_uplift_ratio: float


class PolicyDecision(BaseModel):
    """An auditable gate decision for a strategy before human approval."""

    decision: PolicyDecisionStatus
    strategy: Strategy
    rule_id: str
    reason: str
    evidence: PolicyEvidence


class PolicyDecisionsResponse(BaseModel):
    """Policy decisions derived from deterministic strategies."""

    count: int
    decisions: List[PolicyDecision]
