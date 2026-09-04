from app.models import Opportunity
from app.policy import MAX_REVIEW_UPLIFT_RATIO, evaluate_strategies, evaluate_strategy
from app.strategies import generate_strategies


def make_strategy(uplift_ratio=1.0):
    opportunity = Opportunity(
        opportunity_type="high_value_order",
        source_order_id="order_high",
        currency="INR",
        observed_amount=100 * (1 + uplift_ratio),
        baseline_amount=100,
        uplift_ratio=uplift_ratio,
        explanation="Order-level evidence only.",
    )
    return generate_strategies([opportunity])[0]


def test_valid_strategy_is_allowed():
    decision = evaluate_strategy(make_strategy())

    assert decision.decision == "ALLOW"
    assert decision.rule_id == "all_policy_rules_passed"
    assert decision.evidence.maximum_allowed_uplift_ratio == MAX_REVIEW_UPLIFT_RATIO


def test_uplift_at_maximum_is_allowed():
    decision = evaluate_strategy(make_strategy(uplift_ratio=3.0))

    assert decision.decision == "ALLOW"


def test_uplift_above_maximum_is_blocked():
    decision = evaluate_strategy(make_strategy(uplift_ratio=3.01))

    assert decision.decision == "BLOCK"
    assert decision.rule_id == "maximum_uplift_ratio_exceeded"
    assert "301% exceeds the maximum allowed 300%" in decision.reason


def test_payment_link_amount_mismatch_is_blocked():
    strategy = make_strategy()

    mismatched_parameters = strategy.proposed_action.parameters.model_copy(
        update={"amount": 999}
    )
    mismatched_strategy = strategy.model_copy(
        update={
            "proposed_action": strategy.proposed_action.model_copy(
                update={"parameters": mismatched_parameters}
            )
        }
    )

    decision = evaluate_strategy(mismatched_strategy)

    assert decision.decision == "BLOCK"
    assert decision.rule_id == "payment_link_amount_mismatch"


def test_payment_link_currency_mismatch_is_blocked():
    strategy = make_strategy()

    mismatched_parameters = strategy.proposed_action.parameters.model_copy(
        update={"currency": "USD"}
    )
    mismatched_strategy = strategy.model_copy(
        update={
            "proposed_action": strategy.proposed_action.model_copy(
                update={"parameters": mismatched_parameters}
            )
        }
    )

    decision = evaluate_strategy(mismatched_strategy)

    assert decision.decision == "BLOCK"
    assert decision.rule_id == "payment_link_currency_mismatch"


def test_payment_link_reference_mismatch_is_blocked():
    strategy = make_strategy()

    mismatched_parameters = strategy.proposed_action.parameters.model_copy(
        update={"reference_id": "unexpected-reference"}
    )
    mismatched_strategy = strategy.model_copy(
        update={
            "proposed_action": strategy.proposed_action.model_copy(
                update={"parameters": mismatched_parameters}
            )
        }
    )

    decision = evaluate_strategy(mismatched_strategy)

    assert decision.decision == "BLOCK"
    assert decision.rule_id == "payment_link_reference_mismatch"


def test_unsupported_action_type_is_blocked():
    strategy = make_strategy()
    strategy.proposed_action.action_type = "create_payment"

    decision = evaluate_strategy(strategy)

    assert decision.decision == "BLOCK"
    assert decision.rule_id == "action_type_not_allowlisted"
    assert "create_payment" in decision.reason


def test_policy_evaluation_is_deterministic():
    strategy = make_strategy()

    assert evaluate_strategy(strategy) == evaluate_strategy(strategy)


def test_empty_strategy_list_produces_no_decisions():
    assert evaluate_strategies([]) == []


def test_policy_output_describes_bounded_action_without_unsupported_claims():
    decision = evaluate_strategy(make_strategy())
    combined_text = f"{decision.reason} {decision.rule_id}".lower()

    assert "customer" not in combined_text
    assert "product" not in combined_text
    assert "campaign" not in combined_text
    assert "amount" in combined_text
    assert "currency" in combined_text