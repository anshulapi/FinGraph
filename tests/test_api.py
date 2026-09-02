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
