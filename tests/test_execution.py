"""Tests for the FinGraph execution layer."""

from datetime import datetime, timezone

import pytest

from app.approvals import create_approval
from app.execution import ExecutionNotAllowedError, execute_approved_action
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
    opportunity = Opportunity(
        opportunity_type="high_value_order",
        source_order_id="order_execution_test",
        currency="INR",
        observed_amount=20000,
        baseline_amount=10000.0,
        uplift_ratio=1.0,
        explanation="Order-level value signal.",
    )

    strategy = Strategy(
        opportunity=opportunity,
        proposed_action=StrategyAction(
            action_type="create_payment_link",
            parameters=CreatePaymentLinkStrategyParameters(
                amount=20000,
                currency="INR",
                reference_id="fingraph-order_execution_test",
                description="FinGraph growth action for order order_execution_test",
            ),
        ),
        reasoning="Bounded payment-link strategy.",
        expected_outcome=(
            "Creates a Razorpay Payment Link after policy and human approval."
        ),
        confidence="low",
        confidence_rationale="Limited order-level evidence.",
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
            source_order_id="order_execution_test",
            currency="INR",
            observed_amount=20000,
            baseline_amount=10000.0,
            uplift_ratio=1.0,
            maximum_allowed_uplift_ratio=3.0,
        ),
    )


def make_approval():
    policy_decision = make_policy_decision("ALLOW")

    return create_approval(
        ApprovalRequest(
            policy_decision=policy_decision,
            action="APPROVE",
            approver="demo-reviewer",
            reason="Approved for execution testing.",
        ),
        decided_at=datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
    )


class FakeRazorpayClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create_payment_link(
        self,
        *,
        amount,
        currency,
        reference_id,
        description,
    ):
        self.calls.append(
            {
                "amount": amount,
                "currency": currency,
                "reference_id": reference_id,
                "description": description,
            }
        )

        if self.error is not None:
            raise self.error

        return self.response


def test_approved_action_executes_payment_link():
    client = FakeRazorpayClient(
        response={
            "id": "plink_test_123",
            "short_url": "https://rzp.io/i/test123",
            "status": "created",
        }
    )

    result = execute_approved_action(
        make_approval(),
        razorpay_client=client,
        executed_at=datetime(2026, 9, 5, 10, 1, tzinfo=timezone.utc),
    )

    assert result.status == "SUCCESS"
    assert result.provider_id == "plink_test_123"
    assert result.provider_url == "https://rzp.io/i/test123"
    assert result.provider_status == "created"
    assert result.error is None

    assert client.calls == [
        {
            "amount": 20000,
            "currency": "INR",
            "reference_id": "fingraph-order_execution_test",
            "description": "FinGraph growth action for order order_execution_test",
        }
    ]


def test_rejected_approval_cannot_execute():
    policy_decision = make_policy_decision("ALLOW")

    approval = create_approval(
        ApprovalRequest(
            policy_decision=policy_decision,
            action="REJECT",
            approver="demo-reviewer",
            reason="Rejected for execution testing.",
        ),
        decided_at=datetime(2026, 9, 5, 10, 2, tzinfo=timezone.utc),
    )

    client = FakeRazorpayClient(
        response={
            "id": "should_not_be_created",
        }
    )

    with pytest.raises(
        ExecutionNotAllowedError,
        match="only allowed for an APPROVED human decision",
    ):
        execute_approved_action(
            approval,
            razorpay_client=client,
            executed_at=datetime(2026, 9, 5, 10, 3, tzinfo=timezone.utc),
        )

    assert client.calls == []


def test_blocked_policy_cannot_execute():
    policy_decision = make_policy_decision("BLOCK")

    # A BLOCK decision cannot normally become an ApprovalResult through
    # create_approval(), so construct the impossible state explicitly only
    # to verify that the execution boundary remains defensive.
    from app.models import ApprovalResult

    approval = ApprovalResult(
        policy_decision=policy_decision,
        status="APPROVED",
        approver="demo-reviewer",
        reason="Synthetic defensive test.",
        decided_at=datetime(2026, 9, 5, 10, 4, tzinfo=timezone.utc),
    )

    client = FakeRazorpayClient(
        response={
            "id": "should_not_be_created",
        }
    )

    with pytest.raises(
        ExecutionNotAllowedError,
        match="BLOCK policy decision",
    ):
        execute_approved_action(
            approval,
            razorpay_client=client,
            executed_at=datetime(2026, 9, 5, 10, 5, tzinfo=timezone.utc),
        )

    assert client.calls == []


def test_provider_failure_becomes_failed_execution_result():
    client = FakeRazorpayClient(
        error=RuntimeError("Razorpay Test Mode unavailable")
    )

    result = execute_approved_action(
        make_approval(),
        razorpay_client=client,
        executed_at=datetime(2026, 9, 5, 10, 6, tzinfo=timezone.utc),
    )

    assert result.status == "FAILED"
    assert result.provider_id is None
    assert result.provider_url is None
    assert result.provider_status is None
    assert result.error == "Razorpay Test Mode unavailable"
    assert len(client.calls) == 1


def test_execution_result_preserves_bounded_action():
    client = FakeRazorpayClient(
        response={
            "id": "plink_test_456",
            "short_url": "https://rzp.io/i/test456",
            "status": "created",
        }
    )

    result = execute_approved_action(
        make_approval(),
        razorpay_client=client,
        executed_at=datetime(2026, 9, 5, 10, 7, tzinfo=timezone.utc),
    )

    assert result.action.action_type == "create_payment_link"
    assert result.action.parameters.amount == 20000
    assert result.action.parameters.currency == "INR"
    assert result.action.parameters.reference_id == (
        "fingraph-order_execution_test"
    )