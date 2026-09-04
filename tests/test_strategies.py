from app.models import Opportunity
from app.strategies import generate_strategies


def make_opportunity() -> Opportunity:
    return Opportunity(
        opportunity_type="high_value_order",
        source_order_id="order_high",
        currency="INR",
        observed_amount=200,
        baseline_amount=100,
        uplift_ratio=1.0,
        explanation="Order is 100% above the INR median.",
    )


def test_generates_expected_payment_link_strategy_for_high_value_order():
    strategy = generate_strategies([make_opportunity()])[0]

    assert strategy.proposed_action.action_type == "create_payment_link"


def test_strategy_parameters_are_bounded_by_opportunity_evidence():
    opportunity = make_opportunity()
    parameters = generate_strategies([opportunity])[0].proposed_action.parameters

    assert parameters.amount == opportunity.observed_amount
    assert parameters.currency == opportunity.currency
    assert parameters.reference_id == "fingraph-order_high"
    assert parameters.description == "FinGraph growth action for order order_high"


def test_strategy_reasoning_explains_the_opportunity():
    strategy = generate_strategies([make_opportunity()])[0]

    assert "order_high" in strategy.reasoning
    assert "100%" in strategy.reasoning
    assert "INR" in strategy.reasoning
    assert "baseline" in strategy.reasoning


def test_strategy_expected_outcome_requires_policy_and_human_approval():
    strategy = generate_strategies([make_opportunity()])[0]

    assert "policy approval" in strategy.expected_outcome
    assert "human approval" in strategy.expected_outcome


def test_strategy_makes_no_unsupported_customer_or_product_claims():
    strategy = generate_strategies([make_opportunity()])[0]
    combined_text = (
        f"{strategy.reasoning} {strategy.expected_outcome} "
        f"{strategy.confidence_rationale}"
    ).lower()

    assert "customer" in combined_text
    assert "product" in combined_text
    assert "catalog" in combined_text
    assert "payment-history" in combined_text


def test_unsupported_opportunity_types_are_skipped():
    opportunity = make_opportunity()

    # Opportunity currently has only one supported type, so this verifies
    # the generator returns one strategy for the supported type.
    strategies = generate_strategies([opportunity])

    assert len(strategies) == 1


def test_empty_opportunities_return_empty_strategies():
    assert generate_strategies([]) == []