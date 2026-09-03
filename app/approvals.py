"""Pure human approval domain logic."""

from __future__ import annotations

from datetime import datetime

from app.models import ApprovalRequest, ApprovalResult


class ApprovalNotAllowedError(ValueError):
    """Raised when a policy decision cannot enter human approval."""


def create_approval(
    request: ApprovalRequest,
    *,
    decided_at: datetime,
) -> ApprovalResult:
    """Create an explicit human approval or rejection result.

    Only strategies that passed the policy gate with ALLOW may enter
    the human approval stage.
    """

    if request.policy_decision.decision != "ALLOW":
        raise ApprovalNotAllowedError(
            "Human approval is not allowed for a BLOCK policy decision."
        )

    status = "APPROVED" if request.action == "APPROVE" else "REJECTED"

    return ApprovalResult(
        policy_decision=request.policy_decision,
        status=status,
        approver=request.approver,
        reason=request.reason,
        decided_at=decided_at,
    )