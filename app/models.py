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


class CreatePaymentLinkStrategyParameters(BaseModel):
    """Bounded parameters proposed for a Razorpay Payment Link."""

    amount: int = Field(
        gt=0,
        description="Amount in the smallest currency unit.",
    )
    currency: str
    reference_id: str = Field(min_length=1)
    description: str = Field(min_length=1)


class StrategyAction(BaseModel):
    """A typed executable action proposal that remains gated."""

    action_type: Literal["create_payment_link"]
    parameters: CreatePaymentLinkStrategyParameters


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
ApprovalAction = Literal["APPROVE", "REJECT"]
ApprovalStatus = Literal["APPROVED", "REJECTED"]


class ApprovalRequest(BaseModel):
    """An explicit human decision on an ALLOW policy decision."""

    policy_decision: PolicyDecision
    action: ApprovalAction
    approver: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ApprovalResult(BaseModel):
    """The result of an explicit human approval or rejection."""

    policy_decision: PolicyDecision
    status: ApprovalStatus
    approver: str
    reason: str
    decided_at: datetime


class CreatePaymentLinkParameters(BaseModel):
    """Bounded parameters for creating a Razorpay Payment Link."""

    amount: int = Field(
        gt=0,
        description="Amount in the smallest currency unit.",
    )
    currency: str
    reference_id: str = Field(min_length=1)
    description: str = Field(min_length=1)


class ExecutionAction(BaseModel):
    """A typed executable action approved before execution."""

    action_type: Literal["create_payment_link"]
    parameters: CreatePaymentLinkParameters


ExecutionStatus = Literal["SUCCESS", "FAILED"]


class ExecutionResult(BaseModel):
    """Normalized result of an execution attempt."""

    status: ExecutionStatus
    action: ExecutionAction
    provider_id: Optional[str] = None
    provider_url: Optional[str] = None
    provider_status: Optional[str] = None
    error: Optional[str] = None
    executed_at: datetime