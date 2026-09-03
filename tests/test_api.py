from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.models import NormalizedOrder
from app.razorpay import RazorpayNetworkError


def test_orders_endpoint_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    response = TestClient(app).get("/api/razorpay/orders")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Razorpay Test Mode credentials are not configured. "
        "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
    )


def test_opportunities_endpoint_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    response = TestClient(app).get("/api/opportunities")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Razorpay Test Mode credentials are not configured. "
        "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
    )


def test_opportunities_endpoint_returns_detected_opportunity(monkeypatch):
    class FakeRazorpayClient:
        def __init__(self, settings):
            pass

        def list_orders(self, *, count, skip):
            return [
                NormalizedOrder(
                    id="order_low_one",
                    amount=100,
                    currency="INR",
                    status="created",
                    created_at="2024-01-01T00:00:00Z",
                ),
                NormalizedOrder(
                    id="order_low_two",
                    amount=100,
                    currency="INR",
                    status="created",
                    created_at="2024-01-02T00:00:00Z",
                ),
                NormalizedOrder(
                    id="order_high",
                    amount=150,
                    currency="INR",
                    status="created",
                    created_at="2024-01-03T00:00:00Z",
                ),
            ]

        def close(self):
            pass

    monkeypatch.setattr("app.main.Settings.from_environment", lambda: Settings("rzp_test_example", "secret"))
    monkeypatch.setattr("app.main.RazorpayClient", FakeRazorpayClient)

    response = TestClient(app).get("/api/opportunities")

    assert response.status_code == 200
    assert response.json() == {
        "count": 1,
        "opportunities": [
            {
                "opportunity_type": "high_value_order",
                "source_order_id": "order_high",
                "currency": "INR",
                "observed_amount": 150,
                "baseline_amount": 100.0,
                "uplift_ratio": 0.5,
                "explanation": (
                    "Order order_high is 50% above the INR median order amount of 100. "
                    "This is an order-level value signal only; no customer or product "
                    "inference is made."
                ),
            }
        ],
    }


def test_opportunities_endpoint_maps_upstream_error_safely(monkeypatch):
    class FailingRazorpayClient:
        def __init__(self, settings):
            pass

        def list_orders(self, *, count, skip):
            raise RazorpayNetworkError("provider details must not be exposed")

        def close(self):
            pass

    monkeypatch.setattr("app.main.Settings.from_environment", lambda: Settings("rzp_test_example", "secret"))
    monkeypatch.setattr("app.main.RazorpayClient", FailingRazorpayClient)

    response = TestClient(app).get("/api/opportunities")

    assert response.status_code == 503
    assert response.json() == {"detail": "Razorpay Test Mode is unavailable."}


def test_strategies_endpoint_returns_review_only_strategy(monkeypatch):
    class FakeRazorpayClient:
        def __init__(self, settings):
            pass

        def list_orders(self, *, count, skip):
            return [
                NormalizedOrder(
                    id="order_low_one",
                    amount=100,
                    currency="INR",
                    status="created",
                    created_at="2024-01-01T00:00:00Z",
                ),
                NormalizedOrder(
                    id="order_low_two",
                    amount=100,
                    currency="INR",
                    status="created",
                    created_at="2024-01-02T00:00:00Z",
                ),
                NormalizedOrder(
                    id="order_high",
                    amount=150,
                    currency="INR",
                    status="created",
                    created_at="2024-01-03T00:00:00Z",
                ),
            ]

        def close(self):
            pass

    monkeypatch.setattr("app.main.Settings.from_environment", lambda: Settings("rzp_test_example", "secret"))
    monkeypatch.setattr("app.main.RazorpayClient", FakeRazorpayClient)

    response = TestClient(app).get("/api/strategies")

    assert response.status_code == 200
    strategy = response.json()["strategies"][0]
    assert response.json()["count"] == 1
    assert strategy["proposed_action"]["action_type"] == "review_high_value_order"
    assert strategy["proposed_action"]["parameters"]["source_order_id"] == "order_high"
    assert strategy["confidence"] == "low"


def test_strategies_endpoint_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    response = TestClient(app).get("/api/strategies")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Razorpay Test Mode credentials are not configured. "
        "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
    )


def test_strategies_endpoint_maps_upstream_error_safely(monkeypatch):
    class FailingRazorpayClient:
        def __init__(self, settings):
            pass

        def list_orders(self, *, count, skip):
            raise RazorpayNetworkError("provider details must not be exposed")

        def close(self):
            pass

    monkeypatch.setattr("app.main.Settings.from_environment", lambda: Settings("rzp_test_example", "secret"))
    monkeypatch.setattr("app.main.RazorpayClient", FailingRazorpayClient)

    response = TestClient(app).get("/api/strategies")

    assert response.status_code == 503
    assert response.json() == {"detail": "Razorpay Test Mode is unavailable."}


def test_policy_decisions_endpoint_returns_allowed_decision(monkeypatch):
    class FakeRazorpayClient:
        def __init__(self, settings):
            pass

        def list_orders(self, *, count, skip):
            return [
                NormalizedOrder(
                    id="order_low_one",
                    amount=100,
                    currency="INR",
                    status="created",
                    created_at="2024-01-01T00:00:00Z",
                ),
                NormalizedOrder(
                    id="order_low_two",
                    amount=100,
                    currency="INR",
                    status="created",
                    created_at="2024-01-02T00:00:00Z",
                ),
                NormalizedOrder(
                    id="order_high",
                    amount=150,
                    currency="INR",
                    status="created",
                    created_at="2024-01-03T00:00:00Z",
                ),
            ]

        def close(self):
            pass

    monkeypatch.setattr("app.main.Settings.from_environment", lambda: Settings("rzp_test_example", "secret"))
    monkeypatch.setattr("app.main.RazorpayClient", FakeRazorpayClient)

    response = TestClient(app).get("/api/policy-decisions")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["decisions"][0]["decision"] == "ALLOW"
    assert response.json()["decisions"][0]["rule_id"] == "all_policy_rules_passed"


def test_policy_decisions_endpoint_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    response = TestClient(app).get("/api/policy-decisions")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Razorpay Test Mode credentials are not configured. "
        "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
    )


def test_policy_decisions_endpoint_maps_upstream_error_safely(monkeypatch):
    class FailingRazorpayClient:
        def __init__(self, settings):
            pass

        def list_orders(self, *, count, skip):
            raise RazorpayNetworkError("provider details must not be exposed")

        def close(self):
            pass

    monkeypatch.setattr("app.main.Settings.from_environment", lambda: Settings("rzp_test_example", "secret"))
    monkeypatch.setattr("app.main.RazorpayClient", FailingRazorpayClient)

    response = TestClient(app).get("/api/policy-decisions")

    assert response.status_code == 503
    assert response.json() == {"detail": "Razorpay Test Mode is unavailable."}
def make_allow_policy_decision_payload():
    """Build a representative ALLOW policy decision for API tests."""
    return {
    "decision": "ALLOW",
    "strategy": {
        "opportunity": {
            "opportunity_type": "high_value_order",
            "source_order_id": "order_api_test",
            "currency": "INR",
            "observed_amount": 15000,
            "baseline_amount": 10000.0,
            "uplift_ratio": 0.5,
            "explanation": (
                "Order order_api_test is 50% above the INR median "
                "order amount of 10000. This is an order-level value "
                "signal only; no customer or product inference is made."
            ),
        },
        "proposed_action": {
            "action_type": "review_high_value_order",
            "parameters": {
                "source_order_id": "order_api_test",
                "currency": "INR",
                "observed_amount": 15000,
                "baseline_amount": 10000.0,
                "uplift_ratio": 0.5,
            },
        },
        "reasoning": (
            "Review the order-level value signal before considering "
            "any future action."
        ),
        "expected_outcome": (
            "Creates a human-reviewable record of the order-level "
            "value signal."
        ),
        "confidence": "low",
        "confidence_rationale": (
            "Confidence is low because customer, product, catalog, "
            "and payment-history context is unavailable."
        ),
    },
    "rule_id": "all_policy_rules_passed",
    "reason": (
        "Strategy uses the allowlisted review action, its parameters "
        "match the opportunity evidence, and its uplift ratio is within "
        "the maximum allowed limit."
    ),
    "evidence": {
        "action_type": "review_high_value_order",
        "source_order_id": "order_api_test",
        "currency": "INR",
        "observed_amount": 15000,
        "baseline_amount": 10000.0,
        "uplift_ratio": 0.5,
        "maximum_allowed_uplift_ratio": 3.0,
    },
}


def test_approvals_endpoint_approves_allowed_decision():
    """An explicit APPROVE action returns APPROVED."""
    response = TestClient(app).post(
        "/api/approvals",
        json={
            "policy_decision": make_allow_policy_decision_payload(),
            "action": "APPROVE",
            "approver": "demo-reviewer",
            "reason": "Reviewed the policy evidence and approved the next step.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["approver"] == "demo-reviewer"
    assert body["reason"] == (
        "Reviewed the policy evidence and approved the next step."
    )
    assert body["policy_decision"]["decision"] == "ALLOW"
    assert "decided_at" in body


def test_approvals_endpoint_rejects_allowed_decision():
    """An explicit REJECT action returns REJECTED."""
    response = TestClient(app).post(
        "/api/approvals",
        json={
            "policy_decision": make_allow_policy_decision_payload(),
            "action": "REJECT",
            "approver": "demo-reviewer",
            "reason": "I do not want this strategy to proceed.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["approver"] == "demo-reviewer"
    assert body["reason"] == "I do not want this strategy to proceed."
    assert body["policy_decision"]["decision"] == "ALLOW"
    assert "decided_at" in body


def test_approvals_endpoint_blocks_policy_block():
    """A BLOCK policy decision cannot enter the approval flow."""
    policy_decision = make_allow_policy_decision_payload()
    policy_decision["decision"] = "BLOCK"
    policy_decision["rule_id"] = "maximum_uplift_ratio_exceeded"
    policy_decision["reason"] = (
        "Order uplift exceeds the maximum allowed limit."
    )

    response = TestClient(app).post(
        "/api/approvals",
        json={
            "policy_decision": policy_decision,
            "action": "APPROVE",
            "approver": "demo-reviewer",
            "reason": "Attempting to approve a blocked strategy.",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Human approval is not allowed for a BLOCK policy decision."
    }


def test_approvals_endpoint_validates_missing_approval_metadata():
    """Missing human approval metadata is rejected by FastAPI validation."""
    response = TestClient(app).post(
        "/api/approvals",
        json={
            "policy_decision": make_allow_policy_decision_payload(),
            "action": "APPROVE",
            "approver": "",
            "reason": "",
        },
    )

    assert response.status_code == 422
