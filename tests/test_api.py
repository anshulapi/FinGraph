from fastapi.testclient import TestClient

from app.main import app


def test_orders_endpoint_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    response = TestClient(app).get("/api/razorpay/orders")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Razorpay Test Mode credentials are not configured. "
        "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
    )
