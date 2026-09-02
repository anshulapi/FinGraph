"""Pure deterministic strategy generation from order-level opportunities."""

from __future__ import annotations

from typing import List, Sequence

from app.models import (
    HighValueOrderReviewParameters,
    Opportunity,
    Strategy,
    StrategyAction,
)


def generate_strategies(opportunities: Sequence[Opportunity]) -> List[Strategy]:
    """Generate one conservative review strategy for each supported opportunity.

    The current data contains only order-level evidence. Strategies therefore
    propose a review-only action and make no customer, product, discount,
    campaign, or payment recommendation.
    """
    strategies: List[Strategy] = []
    for opportunity in opportunities:
        if opportunity.opportunity_type != "high_value_order":
            continue

        parameters = HighValueOrderReviewParameters(
            source_order_id=opportunity.source_order_id,
            currency=opportunity.currency,
            observed_amount=opportunity.observed_amount,
            baseline_amount=opportunity.baseline_amount,
            uplift_ratio=opportunity.uplift_ratio,
        )
        strategies.append(
            Strategy(
                opportunity=opportunity,
                proposed_action=StrategyAction(
                    action_type="review_high_value_order",
                    parameters=parameters,
                ),
                reasoning=(
                    f"Order {opportunity.source_order_id} is {opportunity.uplift_ratio:.0%} "
                    f"above the {opportunity.currency} baseline of "
                    f"{opportunity.baseline_amount:g}. Review this order-level value "
                    "signal before considering any future action."
                ),
                expected_outcome=(
                    "Creates a human-reviewable record of the order-level value signal; "
                    "it does not contact a customer, select a product, offer a discount, "
                    "send a campaign, or create a payment."
                ),
                confidence="low",
                confidence_rationale=(
                    "Confidence is low because the available evidence has no customer, "
                    "product, catalog, or payment-history context."
                ),
            )
        )

    return strategies
