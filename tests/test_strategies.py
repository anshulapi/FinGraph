from app.models import Opportunity
from app.strategies import generate_strategies


def make_opportunity():
    return Opportunity(
        opportunity_type="high_value_order",
        source_order_id="order_high",
        currency="INR",
        observed_amount=200,
        baseline_amount=100,
        uplift_ratio=1.0,
        explanation="Order-level evidence only.",
    )


def test_generates_expected_review_strategy_for_high_value_order():
    strategy = generate_strategies([make_opportunity()])[0]

    assert strategy.proposed_action.action_type == "review_high_value_order"
    assert strategy.opportunity == make_opportunity()
    assert "100% above the INR baseline of 100" in strategy.reasoning


def test_empty_opportunities_produce_no_strategies():
    assert generate_strategies([]) == []


def test_strategy_generation_is_deterministic():
    opportunities = [make_opportunity()]

    assert generate_strategies(opportunities) == generate_strategies(opportunities)


def test_action_parameters_mirror_opportunity_evidence():
    opportunity = make_opportunity()
    parameters = generate_strategies([opportunity])[0].proposed_action.parameters

    assert parameters.model_dump() == {
        "source_order_id": opportunity.source_order_id,
        "currency": opportunity.currency,
        "observed_amount": opportunity.observed_amount,
        "baseline_amount": opportunity.baseline_amount,
        "uplift_ratio": opportunity.uplift_ratio,
    }


def test_strategy_makes_no_unsupported_customer_or_product_claims():
    strategy = generate_strategies([make_opportunity()])[0]
    combined_text = f"{strategy.reasoning} {strategy.expected_outcome}".lower()

    assert "customer" in combined_text
    assert "product" in combined_text
    assert "discount" in combined_text
    assert "campaign" in combined_text
    assert "payment" in combined_text
    assert "recommend" not in combined_text


def test_strategy_confidence_and_rationale_are_conservative():
    strategy = generate_strategies([make_opportunity()])[0]

    assert strategy.confidence == "low"
    assert "no customer, product, catalog, or payment-history context" in strategy.confidence_rationale


def test_strategy_contains_no_raw_razorpay_fields():
    strategy = generate_strategies([make_opportunity()])[0]

    assert "notes" not in strategy.model_dump_json()
    assert "amount_paid" not in strategy.model_dump_json()
    assert "amount_due" not in strategy.model_dump_json()
