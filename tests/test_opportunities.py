from app.models import NormalizedOrder
from app.opportunities import detect_opportunities


def make_order(order_id, amount, currency="INR"):
    return NormalizedOrder(
        id=order_id,
        amount=amount,
        currency=currency,
        status="created",
        created_at="2024-01-01T00:00:00Z",
    )


def test_detects_high_value_order():
    opportunities = detect_opportunities(
        [make_order("low_one", 100), make_order("low_two", 100), make_order("high", 200)]
    )

    assert len(opportunities) == 1
    assert opportunities[0].source_order_id == "high"
    assert opportunities[0].baseline_amount == 100
    assert opportunities[0].uplift_ratio == 1.0


def test_returns_no_opportunity_below_threshold():
    opportunities = detect_opportunities(
        [make_order("one", 100), make_order("two", 100), make_order("three", 149)]
    )

    assert opportunities == []


def test_handles_insufficient_orders_safely():
    opportunities = detect_opportunities([make_order("one", 100), make_order("two", 500)])

    assert opportunities == []


def test_includes_order_at_threshold_boundary():
    opportunities = detect_opportunities(
        [make_order("one", 100), make_order("two", 100), make_order("boundary", 150)]
    )

    assert [opportunity.source_order_id for opportunity in opportunities] == ["boundary"]
    assert opportunities[0].uplift_ratio == 0.5


def test_detection_evidence_is_deterministic():
    orders = [make_order("one", 100), make_order("two", 100), make_order("high", 200)]

    assert detect_opportunities(orders) == detect_opportunities(orders)


def test_multiple_currencies_are_never_mixed():
    opportunities = detect_opportunities(
        [
            make_order("inr_one", 100, "INR"),
            make_order("inr_two", 100, "INR"),
            make_order("inr_high", 200, "INR"),
            make_order("usd_one", 1, "USD"),
            make_order("usd_two", 1, "USD"),
        ]
    )

    assert [opportunity.source_order_id for opportunity in opportunities] == ["inr_high"]
    assert opportunities[0].currency == "INR"
    assert opportunities[0].baseline_amount == 100


def test_opportunity_does_not_leak_raw_razorpay_fields():
    opportunity = detect_opportunities(
        [make_order("one", 100), make_order("two", 100), make_order("high", 200)]
    )[0]

    assert set(opportunity.model_dump()) == {
        "opportunity_type",
        "source_order_id",
        "currency",
        "observed_amount",
        "baseline_amount",
        "uplift_ratio",
        "explanation",
    }
