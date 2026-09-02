"""Pure deterministic opportunity detection from normalized order data."""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import DefaultDict, List, Sequence

from app.models import NormalizedOrder, Opportunity

MIN_ORDERS_PER_CURRENCY = 3
"""Minimum same-currency sample size required to establish an order-value baseline."""

HIGH_VALUE_UPLIFT_RATIO = 0.50
"""An order is high-value when it is at least 50% above its currency median."""


def detect_opportunities(orders: Sequence[NormalizedOrder]) -> List[Opportunity]:
    """Identify high-value orders using only deterministic order-level evidence.

    Orders are grouped by currency. A group needs at least three orders, and an
    order qualifies when its amount is at least 50% above that group's median
    amount. Zero or negative baselines are skipped to avoid invalid ratios.
    The result intentionally makes no customer-level or product-level claim.
    """
    orders_by_currency: DefaultDict[str, List[NormalizedOrder]] = defaultdict(list)
    for order in orders:
        orders_by_currency[order.currency].append(order)

    opportunities: List[Opportunity] = []
    for currency in sorted(orders_by_currency):
        currency_orders = orders_by_currency[currency]
        if len(currency_orders) < MIN_ORDERS_PER_CURRENCY:
            continue

        baseline_amount = float(median(order.amount for order in currency_orders))
        if baseline_amount <= 0:
            continue

        for order in currency_orders:
            uplift_ratio = (order.amount - baseline_amount) / baseline_amount
            if uplift_ratio < HIGH_VALUE_UPLIFT_RATIO:
                continue

            opportunities.append(
                Opportunity(
                    opportunity_type="high_value_order",
                    source_order_id=order.id,
                    currency=currency,
                    observed_amount=order.amount,
                    baseline_amount=baseline_amount,
                    uplift_ratio=uplift_ratio,
                    explanation=(
                        f"Order {order.id} is {uplift_ratio:.0%} above the {currency} "
                        f"median order amount of {baseline_amount:g}. This is an "
                        "order-level value signal only; no customer or product inference "
                        "is made."
                    ),
                )
            )

    return sorted(
        opportunities,
        key=lambda opportunity: (
            opportunity.currency,
            -opportunity.uplift_ratio,
            opportunity.source_order_id,
        ),
    )
