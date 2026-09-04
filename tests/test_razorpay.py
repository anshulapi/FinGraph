import httpx
import pytest

from app.config import Settings
from app.razorpay import (
    RazorpayAPIError,
    RazorpayAuthenticationError,
    RazorpayClient,
    RazorpayNetworkError,
    normalize_order,
)


def test_normalize_order_returns_internal_model():
    order = normalize_order(
        {
            "id": "order_123",
            "amount": 2500,
            "currency": "INR",
            "receipt": "receipt_123",
            "status": "created",
            "created_at": 1_700_000_000,
            "notes": {"provider_only": "excluded"},
        }
    )

    assert order.id == "order_123"
    assert order.amount == 2500
    assert order.created_at.isoformat() == "2023-11-14T22:13:20+00:00"
    assert "notes" not in order.model_dump()


def test_client_fetches_and_normalizes_orders():
    def handler(request):
        assert request.url.path == "/v1/orders"
        assert request.url.params["count"] == "2"
        return httpx.Response(
            200,
            json={
                "entity": "collection",
                "count": 1,
                "items": [
                    {
                        "id": "order_123",
                        "amount": 2500,
                        "currency": "INR",
                        "receipt": None,
                        "status": "created",
                        "created_at": 1_700_000_000,
                    }
                ],
            },
        )

    http_client = httpx.Client(
        base_url="https://api.razorpay.com/v1", transport=httpx.MockTransport(handler)
    )
    client = RazorpayClient(
        Settings("rzp_test_example", "test-secret"), http_client=http_client
    )

    orders = client.list_orders(count=2)

    assert len(orders) == 1
    assert orders[0].id == "order_123"


def test_client_maps_authentication_error():
    http_client = httpx.Client(
        base_url="https://api.razorpay.com/v1",
        transport=httpx.MockTransport(lambda request: httpx.Response(401)),
    )
    client = RazorpayClient(Settings("rzp_test_example", "test-secret"), http_client=http_client)

    with pytest.raises(RazorpayAuthenticationError):
        client.list_orders()


def test_client_maps_network_error():
    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    http_client = httpx.Client(
        base_url="https://api.razorpay.com/v1", transport=httpx.MockTransport(handler)
    )
    client = RazorpayClient(Settings("rzp_test_example", "test-secret"), http_client=http_client)

    with pytest.raises(RazorpayNetworkError):
        client.list_orders()
def test_client_creates_payment_link():
    def handler(request):
        assert request.url.path == "/v1/payment_links"
        assert request.method == "POST"

        import json

        body = json.loads(request.content.decode("utf-8"))
        assert body == {
            "amount": 20000,
            "currency": "INR",
            "reference_id": "fingraph-test-link-001",
            "description": "FinGraph approved growth action",
        }
        return httpx.Response(
            200,
            json={
                "id": "plink_test_123",
                "amount": 20000,
                "currency": "INR",
                "reference_id": "fingraph-test-link-001",
                "description": "FinGraph approved growth action",
                "status": "created",
                "short_url": "https://rzp.io/i/test123",
            },
        )

    http_client = httpx.Client(
        base_url="https://api.razorpay.com/v1",
        transport=httpx.MockTransport(handler),
    )
    client = RazorpayClient(
        Settings("rzp_test_example", "test-secret"),
        http_client=http_client,
    )

    result = client.create_payment_link(
        amount=20000,
        currency="INR",
        reference_id="fingraph-test-link-001",
        description="FinGraph approved growth action",
    )

    assert result["id"] == "plink_test_123"
    assert result["short_url"] == "https://rzp.io/i/test123"
    assert result["status"] == "created"


def test_client_maps_payment_link_api_error():
    http_client = httpx.Client(
        base_url="https://api.razorpay.com/v1",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(400)
        ),
    )
    client = RazorpayClient(
        Settings("rzp_test_example", "test-secret"),
        http_client=http_client,
    )

    with pytest.raises(RazorpayAPIError) as exc_info:
        client.create_payment_link(
            amount=20000,
            currency="INR",
            reference_id="fingraph-test-link-002",
            description="FinGraph approved growth action",
        )

    assert exc_info.value.status_code == 400


def test_client_maps_payment_link_network_error():
    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    http_client = httpx.Client(
        base_url="https://api.razorpay.com/v1",
        transport=httpx.MockTransport(handler),
    )
    client = RazorpayClient(
        Settings("rzp_test_example", "test-secret"),
        http_client=http_client,
    )

    with pytest.raises(RazorpayNetworkError):
        client.create_payment_link(
            amount=20000,
            currency="INR",
            reference_id="fingraph-test-link-003",
            description="FinGraph approved growth action",
        )