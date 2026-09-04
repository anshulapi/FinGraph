from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.models import NormalizedOrder
from app.razorpay import RazorpayNetworkError
from app.audit import AuditStore
from datetime import datetime, timezone


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
    assert strategy["proposed_action"]["action_type"] == "create_payment_link"
    assert strategy["proposed_action"]["parameters"]["amount"] == 150
    assert strategy["proposed_action"]["parameters"]["currency"] == "INR"
    assert strategy["proposed_action"]["parameters"]["reference_id"] == "fingraph-order_high"
    assert strategy["proposed_action"]["parameters"]["description"] == (
        "FinGraph growth action for order order_high"
    )
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
                "action_type": "create_payment_link",
                "parameters": {
                    "amount": 15000,
                    "currency": "INR",
                    "reference_id": "fingraph-order_api_test",
                    "description": "FinGraph growth action for order order_api_test",
                },
            },
            "reasoning": (
                "Order order_api_test is 50% above the INR baseline of "
                "10000. Propose a bounded payment-link action using the "
                "observed order amount."
            ),
            "expected_outcome": (
                "Creates a Razorpay Payment Link for the observed order "
                "amount after policy approval and explicit human approval."
            ),
            "confidence": "low",
            "confidence_rationale": (
                "Confidence is low because the available evidence has no "
                "customer, product, catalog, or payment-history context."
            ),
        },
        "rule_id": "all_policy_rules_passed",
        "reason": (
            "Strategy uses the allowlisted Payment Link action, the amount "
            "and currency match the opportunity evidence, the reference "
            "identifies the source order, and the uplift ratio is within "
            "the maximum allowed limit."
        ),
        "evidence": {
            "action_type": "create_payment_link",
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
def test_execution_endpoint_executes_approved_action(monkeypatch):
    """An approved action reaches the Razorpay execution client."""

    calls = []

    class FakeRazorpayClient:
        def __init__(self, settings):
            pass

        def create_payment_link(
            self,
            *,
            amount,
            currency,
            reference_id,
            description,
        ):
            calls.append(
                {
                    "amount": amount,
                    "currency": currency,
                    "reference_id": reference_id,
                    "description": description,
                }
            )
            return {
                "id": "plink_test_123",
                "short_url": "https://rzp.io/i/test123",
                "status": "created",
            }

        def close(self):
            pass

    monkeypatch.setattr(
        "app.main.Settings.from_environment",
        lambda: Settings("rzp_test_example", "secret"),
    )
    monkeypatch.setattr("app.main.RazorpayClient", FakeRazorpayClient)

    approval = {
        "policy_decision": make_allow_policy_decision_payload(),
        "action": "APPROVE",
        "approver": "demo-reviewer",
        "reason": "Approved for execution.",
    }

    approval_response = TestClient(app).post(
        "/api/approvals",
        json=approval,
    )

    assert approval_response.status_code == 200

    execution_response = TestClient(app).post(
        "/api/executions",
        json=approval_response.json(),
    )

    assert execution_response.status_code == 200

    body = execution_response.json()

    assert body["status"] == "SUCCESS"
    assert body["provider_id"] == "plink_test_123"
    assert body["provider_url"] == "https://rzp.io/i/test123"
    assert body["provider_status"] == "created"

    assert body["action"]["action_type"] == "create_payment_link"
    assert body["action"]["parameters"]["amount"] == 15000
    assert body["action"]["parameters"]["currency"] == "INR"

    assert calls == [
        {
            "amount": 15000,
            "currency": "INR",
            "reference_id": "fingraph-order_api_test",
            "description": "FinGraph growth action for order order_api_test",
        }
    ]


def test_execution_endpoint_rejects_rejected_approval(monkeypatch):
    """A rejected human decision cannot reach the provider."""

    calls = []

    class FakeRazorpayClient:
        def __init__(self, settings):
            pass

        def create_payment_link(self, **kwargs):
            calls.append(kwargs)
            return {
                "id": "must_not_execute",
                "short_url": "https://rzp.io/i/never",
                "status": "created",
            }

        def close(self):
            pass

    monkeypatch.setattr(
        "app.main.Settings.from_environment",
        lambda: Settings("rzp_test_example", "secret"),
    )
    monkeypatch.setattr("app.main.RazorpayClient", FakeRazorpayClient)

    approval = {
        "policy_decision": make_allow_policy_decision_payload(),
        "action": "REJECT",
        "approver": "demo-reviewer",
        "reason": "Rejected by reviewer.",
    }

    approval_response = TestClient(app).post(
        "/api/approvals",
        json=approval,
    )

    assert approval_response.status_code == 200

    execution_response = TestClient(app).post(
        "/api/executions",
        json=approval_response.json(),
    )

    assert execution_response.status_code == 409
    assert execution_response.json() == {
        "detail": "Execution is only allowed for an APPROVED human decision."
    }

    assert calls == []


def test_execution_endpoint_rejects_blocked_policy(monkeypatch):
    """A BLOCK decision cannot be executed even if marked APPROVED."""

    calls = []

    class FakeRazorpayClient:
        def __init__(self, settings):
            pass

        def create_payment_link(self, **kwargs):
            calls.append(kwargs)
            return {}

        def close(self):
            pass

    monkeypatch.setattr(
        "app.main.Settings.from_environment",
        lambda: Settings("rzp_test_example", "secret"),
    )
    monkeypatch.setattr("app.main.RazorpayClient", FakeRazorpayClient)

    blocked_policy = make_allow_policy_decision_payload()
    blocked_policy["decision"] = "BLOCK"
    blocked_policy["rule_id"] = "maximum_uplift_ratio_exceeded"
    blocked_policy["reason"] = (
        "Order uplift exceeds the maximum allowed limit."
    )

    execution_response = TestClient(app).post(
        "/api/executions",
        json={
            "policy_decision": blocked_policy,
            "status": "APPROVED",
            "approver": "demo-reviewer",
            "reason": "Attempting to execute a blocked strategy.",
            "decided_at": "2026-09-05T00:00:00Z",
        },
    )

    assert execution_response.status_code == 409
    assert execution_response.json() == {
        "detail": "Execution is not allowed for a BLOCK policy decision."
    }

    assert calls == []


def test_execution_endpoint_returns_failed_result_on_provider_error(monkeypatch):
    """A provider failure is returned as a normalized FAILED execution."""

    class FailingRazorpayClient:
        def __init__(self, settings):
            pass

        def create_payment_link(self, **kwargs):
            raise RazorpayNetworkError("provider unavailable")

        def close(self):
            pass

    monkeypatch.setattr(
        "app.main.Settings.from_environment",
        lambda: Settings("rzp_test_example", "secret"),
    )
    monkeypatch.setattr(
        "app.main.RazorpayClient",
        FailingRazorpayClient,
    )

    approval = {
        "policy_decision": make_allow_policy_decision_payload(),
        "status": "APPROVED",
        "approver": "demo-reviewer",
        "reason": "Approved for execution.",
        "decided_at": "2026-09-05T00:00:00Z",
    }

    response = TestClient(app).post(
        "/api/executions",
        json=approval,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "FAILED"
    assert body["error"] == "provider unavailable"
    assert body["provider_id"] is None
    assert body["provider_url"] is None
    assert body["provider_status"] is None


def test_execution_endpoint_reports_missing_configuration(monkeypatch):
    """Execution cannot start without Razorpay credentials."""

    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    approval = {
        "policy_decision": make_allow_policy_decision_payload(),
        "status": "APPROVED",
        "approver": "demo-reviewer",
        "reason": "Approved for execution.",
        "decided_at": "2026-09-05T00:00:00Z",
    }

    response = TestClient(app).post(
        "/api/executions",
        json=approval,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Razorpay Test Mode credentials are not configured. "
        "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
    )
def test_audit_log_endpoint_returns_persisted_events(tmp_path, monkeypatch):
    """The audit endpoint exposes persisted events."""

    database_path = tmp_path / "audit.db"

    store = AuditStore(str(database_path))

    store.record_event(
        timestamp=datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc),
        stage="policy",
        event_type="policy_evaluation",
        input_data={"source_order_id": "order_test"},
        decision="ALLOW",
        reasoning="Policy rules passed.",
        output_data={"rule_id": "all_policy_rules_passed"},
    )

    monkeypatch.setattr(
        "app.main.AuditStore",
        lambda: AuditStore(str(database_path)),
    )

    response = TestClient(app).get("/api/audit-log")

    assert response.status_code == 200
    assert response.json() == {
        "count": 1,
        "events": [
            {
                "id": 1,
                "timestamp": "2026-09-05T12:00:00+00:00",
                "stage": "policy",
                "event_type": "policy_evaluation",
                "input_data": {
                    "source_order_id": "order_test",
                },
                "decision": "ALLOW",
                "reasoning": "Policy rules passed.",
                "output_data": {
                    "rule_id": "all_policy_rules_passed",
                },
            }
        ],
    }