"""Tests for the human approval domain layer."""

from datetime import datetime, timezone

import pytest

from app.approvals import ApprovalNotAllowedError, create_approval
from app.models import (
    ApprovalRequest,
    CreatePaymentLinkStrategyParameters,
    Opportunity,
    PolicyDecision,
    PolicyEvidence,
    Strategy,
    StrategyAction,
)


def make_policy_decision(decision: str = "ALLOW") -> PolicyDecision:
    """Build a representative policy decision for approval tests."""

    opportunity = Opportunity(
        opportunity_type="high_value_order",
        source_order_id="order_test_001",
        currency="INR",
        observed_amount=20000,
        baseline_amount=10000.0,
        uplift_ratio=1.0,
        explanation=(
            "Order order_test_001 is 100% above the INR median "
            "order amount of 10000."
        ),
    )

    strategy = Strategy(
        opportunity=opportunity,
        proposed_action=StrategyAction(
            action_type="create_payment_link",
            parameters=CreatePaymentLinkStrategyParameters(
                amount=20000,
                currency="INR",
                reference_id="fingraph-order_test_001",
                description="FinGraph growth action for order order_test_001",
            ),
        ),
        reasoning=(
            "Order order_test_001 is 100% above the INR baseline of "
            "10000. Propose a bounded payment-link action using the "
            "observed order amount."
        ),
        expected_outcome=(
            "Creates a Razorpay Payment Link for the observed order "
            "amount after policy approval and explicit human approval."
        ),
        confidence="low",
        confidence_rationale=(
            "Confidence is low because the available evidence has no "
            "customer, product, catalog, or payment-history context."
        ),
    )

    return PolicyDecision(
        decision=decision,
        strategy=strategy,
        rule_id=(
            "all_policy_rules_passed"
            if decision == "ALLOW"
            else "maximum_uplift_ratio_exceeded"
        ),
        reason=(
            "All policy rules passed."
            if decision == "ALLOW"
            else "Order uplift exceeds the maximum allowed limit."
        ),
        evidence=PolicyEvidence(
            action_type="create_payment_link",
            source_order_id="order_test_001",
            currency="INR",
            observed_amount=20000,
            baseline_amount=10000.0,
            uplift_ratio=1.0,
            maximum_allowed_uplift_ratio=3.0,
        ),
    )


def test_allow_decision_can_be_approved() -> None:
    """An ALLOW decision plus explicit APPROVE becomes APPROVED."""

    policy_decision = make_policy_decision("ALLOW")
    decided_at = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)

    request = ApprovalRequest(
        policy_decision=policy_decision,
        action="APPROVE",
        approver="demo-reviewer",
        reason="Reviewed the policy evidence and approved the next step.",
    )

    result = create_approval(request, decided_at=decided_at)

    assert result.status == "APPROVED"
    assert result.approver == "demo-reviewer"
    assert result.reason == request.reason
    assert result.decided_at == decided_at
    assert result.policy_decision == policy_decision


def test_allow_decision_can_be_rejected() -> None:
    """An ALLOW decision plus explicit REJECT becomes REJECTED."""

    policy_decision = make_policy_decision("ALLOW")
    decided_at = datetime(2026, 9, 3, 10, 5, tzinfo=timezone.utc)

    request = ApprovalRequest(
        policy_decision=policy_decision,
        action="REJECT",
        approver="demo-reviewer",
        reason="I do not want this strategy to proceed.",
    )

    result = create_approval(request, decided_at=decided_at)

    assert result.status == "REJECTED"
    assert result.approver == "demo-reviewer"
    assert result.reason == request.reason
    assert result.decided_at == decided_at
    assert result.policy_decision == policy_decision


def test_block_decision_cannot_enter_approval() -> None:
    """A BLOCK decision must never produce an approval result."""

    policy_decision = make_policy_decision("BLOCK")

    request = ApprovalRequest(
        policy_decision=policy_decision,
        action="APPROVE",
        approver="demo-reviewer",
        reason="Attempting to approve a blocked strategy.",
    )

    with pytest.raises(
        ApprovalNotAllowedError,
        match="not allowed for a BLOCK policy decision",
    ):
        create_approval(
            request,
            decided_at=datetime(2026, 9, 3, 10, 10, tzinfo=timezone.utc),
        )


def test_fixed_inputs_and_timestamp_are_deterministic() -> None:
    """Identical inputs and timestamps produce identical results."""

    policy_decision = make_policy_decision("ALLOW")

    request = ApprovalRequest(
        policy_decision=policy_decision,
        action="APPROVE",
        approver="demo-reviewer",
        reason="Approved after reviewing the policy evidence.",
    )

    decided_at = datetime(2026, 9, 3, 10, 15, tzinfo=timezone.utc)

    first = create_approval(request, decided_at=decided_at)
    second = create_approval(request, decided_at=decided_at)

    assert first == second


def test_empty_approver_is_rejected() -> None:
    """Approver must contain at least one character."""

    with pytest.raises(ValueError):
        ApprovalRequest(
            policy_decision=make_policy_decision(),
            action="APPROVE",
            approver="",
            reason="Valid reason.",
        )


def test_empty_reason_is_rejected() -> None:
    """Approval reason must contain at least one character."""

    with pytest.raises(ValueError):
        ApprovalRequest(
            policy_decision=make_policy_decision(),
            action="APPROVE",
            approver="demo-reviewer",
            reason="",
        )


def test_policy_decision_is_preserved_completely() -> None:
    """Approval result keeps the full policy decision and its evidence."""

    policy_decision = make_policy_decision("ALLOW")

    request = ApprovalRequest(
        policy_decision=policy_decision,
        action="APPROVE",
        approver="demo-reviewer",
        reason="Evidence reviewed.",
    )

    result = create_approval(
        request,
        decided_at=datetime(2026, 9, 3, 10, 20, tzinfo=timezone.utc),
    )

    assert result.policy_decision.strategy == policy_decision.strategy
    assert result.policy_decision.evidence == policy_decision.evidence
    assert result.policy_decision.rule_id == "all_policy_rules_passed"