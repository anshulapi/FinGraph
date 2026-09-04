"""Pure deterministic strategy generation from order-level opportunities."""

from __future__ import annotations

from typing import List, Sequence

from app.models import (
    CreatePaymentLinkStrategyParameters,
    Opportunity,
    Strategy,
    StrategyAction,
)


def generate_strategies(opportunities: Sequence[Opportunity]) -> List[Strategy]:
    """Generate one bounded payment-link strategy for each opportunity.

    The action is only a proposal. It is not executed here.
    Human approval remains required before execution.
    """
    strategies: List[Strategy] = []

    for opportunity in opportunities:
        if opportunity.opportunity_type != "high_value_order":
            continue

        parameters = CreatePaymentLinkStrategyParameters(
            amount=opportunity.observed_amount,
            currency=opportunity.currency,
            reference_id=f"fingraph-{opportunity.source_order_id}",
            description=(
                f"FinGraph growth action for order "
                f"{opportunity.source_order_id}"
            ),
        )

        strategies.append(
            Strategy(
                opportunity=opportunity,
                proposed_action=StrategyAction(
                    action_type="create_payment_link",
                    parameters=parameters,
                ),
                reasoning=(
                    f"Order {opportunity.source_order_id} is "
                    f"{opportunity.uplift_ratio:.0%} above the "
                    f"{opportunity.currency} baseline of "
                    f"{opportunity.baseline_amount:g}. "
                    "Propose a bounded payment-link action using "
                    "the observed order amount."
                ),
                expected_outcome=(
                    "Creates a Razorpay Payment Link for the observed "
                    "order amount after policy approval and explicit "
                    "human approval."
                ),
                confidence="low",
                confidence_rationale=(
                    "Confidence is low because the available evidence "
                    "has no customer, product, catalog, or payment-history "
                    "context."
                ),
            )
        )

    return strategies