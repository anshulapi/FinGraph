"""Execution layer for approved FinGraph actions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.models import ApprovalResult, ExecutionAction, ExecutionResult
from app.razorpay import RazorpayClient


class ExecutionNotAllowedError(ValueError):
    """Raised when an action has not received explicit human approval."""


def execute_approved_action(
    approval: ApprovalResult,
    *,
    razorpay_client: RazorpayClient,
    executed_at: datetime,
) -> ExecutionResult:
    """Execute an explicitly approved FinGraph action."""

    if approval.status != "APPROVED":
        raise ExecutionNotAllowedError(
            "Execution is only allowed for an APPROVED human decision."
        )

    policy_decision = approval.policy_decision

    if policy_decision.decision != "ALLOW":
        raise ExecutionNotAllowedError(
            "Execution is not allowed for a BLOCK policy decision."
        )

    strategy = policy_decision.strategy

    if strategy.proposed_action.action_type != "create_payment_link":
        raise ExecutionNotAllowedError(
            "Unsupported execution action."
        )

    parameters = strategy.proposed_action.parameters

    action = ExecutionAction(
        action_type="create_payment_link",
        parameters={
            "amount": parameters.amount,
            "currency": parameters.currency,
            "reference_id": parameters.reference_id,
            "description": parameters.description,
        },
    )

    try:
        response: Dict[str, Any] = razorpay_client.create_payment_link(
            amount=parameters.amount,
            currency=parameters.currency,
            reference_id=parameters.reference_id,
            description=parameters.description,
        )
    except Exception as exc:
        return ExecutionResult(
            status="FAILED",
            action=action,
            error=str(exc),
            executed_at=executed_at,
        )

    return ExecutionResult(
        status="SUCCESS",
        action=action,
        provider_id=response.get("id"),
        provider_url=response.get("short_url"),
        provider_status=response.get("status"),
        executed_at=executed_at,
    )