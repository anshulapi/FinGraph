"""Pure deterministic policy and risk evaluation for FinGraph strategies."""

from __future__ import annotations

from typing import List, Sequence

from app.models import PolicyDecision, PolicyEvidence, Strategy

MAX_REVIEW_UPLIFT_RATIO = 3.0
"""Maximum uplift ratio eligible for progression to human approval."""

ALLOWED_ACTION_TYPE = "create_payment_link"


def _policy_evidence(strategy: Strategy) -> PolicyEvidence:
    """Capture the typed action and opportunity fields used by policy rules."""
    parameters = strategy.proposed_action.parameters
    opportunity = strategy.opportunity

    return PolicyEvidence(
        action_type=str(strategy.proposed_action.action_type),
        source_order_id=opportunity.source_order_id,
        currency=opportunity.currency,
        observed_amount=opportunity.observed_amount,
        baseline_amount=opportunity.baseline_amount,
        uplift_ratio=opportunity.uplift_ratio,
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
    """Allow only bounded, evidence-consistent payment-link strategies.

    Rules are evaluated in a fixed order: action allowlist, payment-link
    parameter validation, evidence validation, then the uplift cap.
    A blocked decision is terminal and cannot advance to human approval.
    """
    if strategy.proposed_action.action_type != ALLOWED_ACTION_TYPE:
        return _block(
            strategy,
            "action_type_not_allowlisted",
            f"Action type '{strategy.proposed_action.action_type}' is not allowlisted.",
        )

    parameters = strategy.proposed_action.parameters
    opportunity = strategy.opportunity

    if parameters.amount != opportunity.observed_amount:
        return _block(
            strategy,
            "payment_link_amount_mismatch",
            "Payment Link amount does not match the observed opportunity amount.",
        )

    if parameters.currency != opportunity.currency:
        return _block(
            strategy,
            "payment_link_currency_mismatch",
            "Payment Link currency does not match the opportunity currency.",
        )

    expected_reference_id = f"fingraph-{opportunity.source_order_id}"
    if parameters.reference_id != expected_reference_id:
        return _block(
            strategy,
            "payment_link_reference_mismatch",
            "Payment Link reference_id does not match the source order.",
        )

    if parameters.description.strip() == "":
        return _block(
            strategy,
            "payment_link_description_invalid",
            "Payment Link description cannot be empty.",
        )

    if parameters.amount <= 0:
        return _block(
            strategy,
            "payment_link_amount_invalid",
            "Payment Link amount must be greater than zero.",
        )

    if parameters.currency != opportunity.currency:
        return _block(
            strategy,
            "strategy_evidence_mismatch",
            "Action parameters do not match the opportunity currency.",
        )

    if opportunity.uplift_ratio > MAX_REVIEW_UPLIFT_RATIO:
        return _block(
            strategy,
            "maximum_uplift_ratio_exceeded",
            f"Order uplift ratio {opportunity.uplift_ratio:.0%} exceeds the maximum "
            f"allowed {MAX_REVIEW_UPLIFT_RATIO:.0%}.",
        )

    return PolicyDecision(
        decision="ALLOW",
        strategy=strategy,
        rule_id="all_policy_rules_passed",
        reason=(
            "Strategy uses the allowlisted Payment Link action, the amount and "
            "currency match the opportunity evidence, the reference identifies "
            "the source order, and the uplift ratio is within the maximum allowed limit."
        ),
        evidence=_policy_evidence(strategy),
    )


def evaluate_strategies(
    strategies: Sequence[Strategy],
) -> List[PolicyDecision]:
    """Evaluate strategies in stable input order without side effects."""
    return [evaluate_strategy(strategy) for strategy in strategies]