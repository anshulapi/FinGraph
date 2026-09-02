"""Pure deterministic policy and risk evaluation for FinGraph strategies."""

from __future__ import annotations

from typing import List, Sequence

from app.models import PolicyDecision, PolicyEvidence, Strategy

MAX_REVIEW_UPLIFT_RATIO = 3.0
"""Maximum uplift ratio eligible for automatic progression to human approval."""

ALLOWED_ACTION_TYPE = "review_high_value_order"


def _policy_evidence(strategy: Strategy) -> PolicyEvidence:
    """Capture exactly the typed action fields used by every policy rule."""
    parameters = strategy.proposed_action.parameters
    return PolicyEvidence(
        action_type=str(strategy.proposed_action.action_type),
        source_order_id=parameters.source_order_id,
        currency=parameters.currency,
        observed_amount=parameters.observed_amount,
        baseline_amount=parameters.baseline_amount,
        uplift_ratio=parameters.uplift_ratio,
        maximum_allowed_uplift_ratio=MAX_REVIEW_UPLIFT_RATIO,
    )


def _block(strategy: Strategy, rule_id: str, reason: str) -> PolicyDecision:
    return PolicyDecision(
        decision="BLOCK",
        strategy=strategy,
        rule_id=rule_id,
        reason=reason,
        evidence=_policy_evidence(strategy),
    )


def evaluate_strategy(strategy: Strategy) -> PolicyDecision:
    """Allow only bounded, evidence-consistent review strategies.

    Rules are evaluated in a fixed order: action allowlist, evidence matching,
    then the uplift cap. A blocked decision is terminal and can be displayed in
    an audit trail; only an allowed decision should advance to human approval.
    """
    if strategy.proposed_action.action_type != ALLOWED_ACTION_TYPE:
        return _block(
            strategy,
            "action_type_not_allowlisted",
            f"Action type '{strategy.proposed_action.action_type}' is not allowlisted.",
        )

    parameters = strategy.proposed_action.parameters
    opportunity = strategy.opportunity
    fields_to_match = (
        "source_order_id",
        "currency",
        "observed_amount",
        "baseline_amount",
        "uplift_ratio",
    )
    mismatched_fields = [
        field for field in fields_to_match if getattr(parameters, field) != getattr(opportunity, field)
    ]
    if mismatched_fields:
        return _block(
            strategy,
            "strategy_evidence_mismatch",
            "Action parameters do not match the opportunity evidence for: "
            + ", ".join(mismatched_fields)
            + ".",
        )

    if parameters.uplift_ratio > MAX_REVIEW_UPLIFT_RATIO:
        return _block(
            strategy,
            "maximum_uplift_ratio_exceeded",
            f"Order uplift ratio {parameters.uplift_ratio:.0%} exceeds the maximum "
            f"allowed {MAX_REVIEW_UPLIFT_RATIO:.0%}.",
        )

    return PolicyDecision(
        decision="ALLOW",
        strategy=strategy,
        rule_id="all_policy_rules_passed",
        reason=(
            "Strategy uses the allowlisted review action, its parameters match the "
            "opportunity evidence, and its uplift ratio is within the maximum allowed limit."
        ),
        evidence=_policy_evidence(strategy),
    )


def evaluate_strategies(strategies: Sequence[Strategy]) -> List[PolicyDecision]:
    """Evaluate strategies in stable input order without side effects."""
    return [evaluate_strategy(strategy) for strategy in strategies]
